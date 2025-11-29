from PIL import Image, ImageDraw
import random
import time
import io
import concurrent.futures
import requests

def generate_similar_color(base_color, variation=150):
    def clamp(value, min_value=0, max_value=255):
        return max(min_value, min(value, max_value))
    return tuple(
        clamp(channel + random.randint(-variation, variation))
        for channel in base_color
    )

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def extend_gif_with_confetti_and_text(frames, extension_frames, top_text, bottom_text, rarity, rarity_color, winner_picture_url, winner_position):
    last_frame = frames[-1]
    width, height = last_frame.size
    base_color = hex_to_rgb(rarity_color)
    density = int((30 * rarity) + 5)
    
    # Fetch and prepare the winner picture
    winner_image = fetch_image_from_url(winner_picture_url)
    if winner_image:
        # Resize to fit nicely in the frame
        winner_image = winner_image.resize((100, 100))
    
    confetti = [
        {
            "x": width // 2,
            "y": (height // 2)+(height * 0.4),
            "vx": random.uniform(-6, 6),
            "vy": random.uniform(-10, -6),
            "color": generate_similar_color(base_color),
        }
        for _ in range(density)
    ]

    for frame_idx in range(extension_frames):
        confetti_frame = last_frame.copy()
        draw = ImageDraw.Draw(confetti_frame)
        
        # After first frame, replace thumbnail with full picture at exact winner position
        if frame_idx > 0 and winner_image and winner_position:
            confetti_frame.paste(winner_image, winner_position)
            
            # Redraw the rarity bar below the winner image using overlay
            overlay = Image.new('RGBA', confetti_frame.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            rarity_rgb = hex_to_rgb(rarity_color)
            bar_height = 25
            bar_y_top = winner_position[1] + 100 - bar_height
            
            for gradient_step in range(bar_height):
                alpha = int((gradient_step / bar_height) * 255)  # 0 at top to 255 at bottom
                color_with_alpha = rarity_rgb + (alpha,)
                overlay_draw.rectangle(
                    [winner_position[0], bar_y_top + gradient_step, winner_position[0] + 100, bar_y_top + gradient_step + 1],
                    fill=color_with_alpha
                )
            
            # Composite the overlay onto the frame
            confetti_frame = confetti_frame.convert('RGBA')
            confetti_frame = Image.alpha_composite(confetti_frame, overlay)
            confetti_frame = confetti_frame.convert('RGB')
            draw = ImageDraw.Draw(confetti_frame)
        
        for particle in confetti:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += 0.3
            particle["x"] %= width
            particle["y"] %= height
            draw.ellipse(
                (particle["x"] - 2, particle["y"] - 2, particle["x"] + 2, particle["y"] + 2),
                fill=particle["color"]
            )
        
        draw.text((width // 2, 10), top_text, fill="white", anchor="mm")
        draw.text((width // 2, height - 30), bottom_text, fill="white", anchor="mm")
        frames.append(confetti_frame)
    
    return frames

def create_crate_unboxing_gif(
    images,
    rarity_colors,
    target_index,
    frame_size=(400, 200),
    spin_duration=2,
    fps=17,
    initial_speed_modifier=1.0,
):
    num_items = len(images)
    total_frames = int(spin_duration * fps)
    item_spacing = 105
    carousel_width = item_spacing * num_items
    center_x, center_y = frame_size[0] // 2, frame_size[1] // 2
    highlight_color = (255, 215, 0)
    frames = []
    winner_position = None

    random_offset = random.uniform(0,1)
    target_offset = (target_index * item_spacing) - (item_spacing * random_offset)
    adjusted_carousel_width = carousel_width * initial_speed_modifier

    for frame_index in range(total_frames):
        progress = frame_index / total_frames
        if progress < 0.9:
            easing = 2 ** (-10 * progress)
        else:
            easing = 2 ** (-10 * 0.9) * (1 - (progress - 0.9) / 0.1)

        offset = easing * adjusted_carousel_width + (1 - easing) * target_offset

        frame = Image.new("RGB", frame_size, (30, 30, 30))
        draw = ImageDraw.Draw(frame)

        for i in range(-2, num_items + 2):
            idx = i % num_items
            img_x = center_x - (i * item_spacing - offset)
            img_y = center_y - 50

            # Draw the highlight box if in the winning zone
            if (center_x - item_spacing) < img_x and img_x < (center_x):
                draw.rectangle(
                    [img_x - 5, img_y - 5, img_x + 105, img_y + 105],
                    outline=highlight_color,
                    width=3,
                )
                # Store the winner position when it's in the highlight area
                if idx == target_index:
                    winner_position = (int(img_x), img_y)

            # Paste the item image first
            frame.paste(images[idx], (int(img_x), img_y))

        # Create overlay for rarity bars with transparency
        overlay = Image.new('RGBA', frame.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        for i in range(-2, num_items + 2):
            idx = i % num_items
            img_x = center_x - (i * item_spacing - offset)
            img_y = center_y - 50
            
            # Draw rarity color bar with fading effect on overlay
            rarity_rgb = hex_to_rgb(rarity_colors[idx])
            bar_height = 25
            bar_y_top = img_y + 100 - bar_height  # Start 25 pixels above the bottom
            
            # Create gradient effect (transparent at top, solid at bottom)
            for gradient_step in range(bar_height):
                alpha = int((gradient_step / bar_height) * 255)  # 0 at top to 255 at bottom
                color_with_alpha = rarity_rgb + (alpha,)
                overlay_draw.rectangle(
                    [int(img_x), bar_y_top + gradient_step, int(img_x) + 100, bar_y_top + gradient_step + 1],
                    fill=color_with_alpha
                )
        
        # Composite the overlay onto the frame
        frame = frame.convert('RGBA')
        frame = Image.alpha_composite(frame, overlay)
        frame = frame.convert('RGB')

        needle_x = center_x - 5
        draw = ImageDraw.Draw(frame)
        draw.polygon(
            [(needle_x, 10), (needle_x + 10, 10), (needle_x + 5, 50)],
            fill="red"
        )

        frames.append(frame)

    for _ in range(fps):
        frames.append(frames[-1])

    return frames, winner_position

def fetch_image_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        print(f"Failed to fetch image from {url}: {e}")
        return None

def preprocess_thumbnail_from_url(url, thumbnail_size=(100, 100), reduce_colors=True):
    image = fetch_image_from_url(url)
    if image is None:
        return None
    image = image.resize(thumbnail_size)
    if reduce_colors:
        image = image.convert("P", palette=Image.ADAPTIVE, colors=256)
    return image

def preprocess_thumbnails_from_urls(urls, thumbnail_size=(100, 100), reduce_colors=True):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        thumbnails = list(
            executor.map(
                preprocess_thumbnail_from_url,
                urls,
                [thumbnail_size] * len(urls),
                [reduce_colors] * len(urls),
            )
        )
    return [thumbnail for thumbnail in thumbnails if thumbnail is not None]

def encode_frame_to_bytes(frame, duration):
    frame_bytes = io.BytesIO()
    frame.save(frame_bytes, format="GIF", duration=duration)
    return frame_bytes.getvalue()

def assemble_gif_from_encoded_frames(encoded_frames, duration=50):
    gif_buffer = io.BytesIO()
    first_frame = Image.open(io.BytesIO(encoded_frames[0]))
    rest_frames = [Image.open(io.BytesIO(f)) for f in encoded_frames[1:]]
    first_frame.save(
        gif_buffer,
        format="GIF",
        save_all=True,
        append_images=rest_frames,
        duration=duration,
        loop=0,
        optimize=False,
    )
    gif_buffer.seek(0)
    return gif_buffer

def parallel_save_gif(frames, duration=50):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        encoded_frames = list(
            executor.map(encode_frame_to_bytes, frames, [duration] * len(frames))
        )
    return assemble_gif_from_encoded_frames(encoded_frames, duration)

def generate_gif(items, winning_item, fps=20):
    """
    Generate a crate unboxing GIF with confetti animation.
    
    Args:
        items: List of dicts with keys: itemThumbnailURL, itemRarityColor, itemRarity (weight)
        winning_item: Dict with keys: itemThumbnailURL, itemPictureURL, 
                      itemRarity (weight), itemRarityColor, itemName
        fps: Frames per second for the GIF
    
    Returns:
        BytesIO object containing the GIF
    """
    start_time = time.time()
    
    # Calculate normalized rarity (inverse of weight proportion)
    # Higher weight = more common = lower rarity value for confetti
    total_weight = sum(item.get('itemRarity', 1) for item in items) + winning_item['itemRarity']
    normalized_rarity = 1.0 - (winning_item['itemRarity'] / total_weight)
    # Scale to 0-10 range for confetti density
    computed_rarity = normalized_rarity * 10
    print(winning_item['itemRarity'])
    print(computed_rarity)
    # Extract thumbnail URLs and rarity colors from items
    thumbnail_urls = [item['itemThumbnailURL'] for item in items]
    rarity_colors = [item['itemRarityColor'] for item in items]
    
    # Randomize winning item placement
    target_index = random.randint(0, len(items) - 1)
    
    # Insert winning item at target position
    items_copy = items.copy()
    items_copy[target_index] = {
        'itemThumbnailURL': winning_item['itemThumbnailURL'],
        'itemRarityColor': winning_item['itemRarityColor']
    }
    thumbnail_urls = [item['itemThumbnailURL'] for item in items_copy]
    rarity_colors = [item['itemRarityColor'] for item in items_copy]
    
    # Preprocess thumbnails
    preprocessed_thumbnails = preprocess_thumbnails_from_urls(
        thumbnail_urls, 
        thumbnail_size=(100, 100), 
        reduce_colors=True
    )
    print("--- %s seconds to preprocess thumbnails ---" % (time.time() - start_time))
    
    # Create spinning animation
    start_time = time.time()
    frames, winner_position = create_crate_unboxing_gif(
        preprocessed_thumbnails * 16,
        rarity_colors * 16,
        target_index, 
        spin_duration=5, 
        fps=fps
    )
    print("--- %s seconds to create frames ---" % (time.time() - start_time))
    
    # Add confetti and text
    top_text = "WINNER!!!"
    bottom_text = winning_item['itemName']
    extension_frames = 5 * fps
    
    start_time = time.time()
    frames = extend_gif_with_confetti_and_text(
        frames, 
        extension_frames, 
        top_text, 
        bottom_text, 
        computed_rarity,  # Use computed rarity instead of raw weight
        winning_item['itemRarityColor'],
        winning_item['itemPictureURL'],
        winner_position
    )
    print("--- %s seconds to add confetti ---" % (time.time() - start_time))
    print(f"Total frames: {len(frames)}")
    
    # Save GIF
    start_time = time.time()
    gif_bytes = parallel_save_gif(frames, duration=int(1000 / fps))
    print("--- %s seconds to save GIF ---" % (time.time() - start_time))
    
    return gif_bytes

# Example usage:
# items = [
#     {'itemThumbnailURL': 'http://...', 'itemRarityColor': '#FF5733', 'itemRarity': 100},
#     {'itemThumbnailURL': 'http://...', 'itemRarityColor': '#33FF57', 'itemRarity': 50},
#     # ... more items
# ]
# 
# winning_item = {
#     'itemThumbnailURL': 'http://...',
#     'itemPictureURL': 'http://...',
#     'itemRarity': 5,  # Low weight = rare item = lots of confetti
#     'itemRarityColor': '#FFD700',
#     'itemName': 'Legendary Sword'
# }
# 
# gif_bytes = generate_gif(items, winning_item, fps=20)
# 
# with open("crate_unboxing.gif", "wb") as f:
#     f.write(gif_bytes.getvalue())
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import random
import time
import io
import math
import concurrent.futures
import requests

def generate_similar_color(base_color, variation=150):
    def clamp(value, min_value=0, max_value=255):
        return max(min_value, min(value, max_value))

    return tuple(
        clamp(channel + random.randint(-variation, variation))
        for channel in base_color
    )

def get_rarity_config(rarity):
    """Get visual configuration based on rarity level."""
    if rarity < 10:
        return {"color": (94, 42, 12), "beams": 0, "shake": 0, "flash": 0, "name": "poop"}
    elif rarity < 50:
        return {"color": (157, 157, 157), "beams": 0, "shake": 0, "flash": 0, "name": "common"}
    elif rarity < 83:
        return {"color": (30, 255, 0), "beams": 4, "shake": 0, "flash": 0.3, "name": "uncommon"}
    elif rarity < 91:
        return {"color": (0, 112, 221), "beams": 6, "shake": 2, "flash": 0.5, "name": "rare"}
    elif rarity < 97:
        return {"color": (163, 53, 238), "beams": 10, "shake": 4, "flash": 0.7, "name": "epic"}
    else:
        return {"color": (255, 215, 0), "beams": 16, "shake": 6, "flash": 1.0, "name": "legendary"}

def draw_light_beams(draw, center_x, center_y, num_beams, beam_length, beam_width, color, rotation_offset=0, alpha=1.0):
    """Draw radiating light beams from a center point."""
    if num_beams == 0:
        return

    for i in range(num_beams):
        angle = (2 * math.pi * i / num_beams) + rotation_offset

        # Calculate beam endpoints
        inner_radius = 30
        outer_radius = inner_radius + beam_length

        # Create beam as a triangle/wedge
        angle_spread = math.pi / (num_beams * 2)

        x1 = center_x + inner_radius * math.cos(angle - angle_spread * 0.3)
        y1 = center_y + inner_radius * math.sin(angle - angle_spread * 0.3)
        x2 = center_x + inner_radius * math.cos(angle + angle_spread * 0.3)
        y2 = center_y + inner_radius * math.sin(angle + angle_spread * 0.3)
        x3 = center_x + outer_radius * math.cos(angle + angle_spread * beam_width)
        y3 = center_y + outer_radius * math.sin(angle + angle_spread * beam_width)
        x4 = center_x + outer_radius * math.cos(angle - angle_spread * beam_width)
        y4 = center_y + outer_radius * math.sin(angle - angle_spread * beam_width)

        # Fade the color based on alpha
        faded_color = tuple(int(c * alpha) for c in color)
        draw.polygon([(x1, y1), (x2, y2), (x3, y3), (x4, y4)], fill=faded_color)

def draw_sparkles(draw, width, height, num_sparkles, frame_index, base_color):
    """Draw twinkling sparkle effects."""
    random.seed(42)  # Consistent sparkle positions
    for i in range(num_sparkles):
        x = random.randint(0, width)
        y = random.randint(0, height)

        # Twinkle effect - vary size based on frame
        phase = (frame_index + i * 7) % 10
        if phase < 5:
            size = phase + 1
        else:
            size = 10 - phase

        if size > 0:
            sparkle_color = tuple(min(255, c + 100) for c in base_color)
            draw.ellipse((x - size, y - size, x + size, y + size), fill=sparkle_color)
            # Cross sparkle
            draw.line((x - size * 2, y, x + size * 2, y), fill="white", width=1)
            draw.line((x, y - size * 2, x, y + size * 2), fill="white", width=1)
    random.seed()  # Reset seed

def apply_screen_shake(frame, shake_amount, frame_index):
    """Apply screen shake effect by offsetting the image."""
    if shake_amount == 0:
        return frame

    # Decreasing shake over time
    current_shake = shake_amount * (1 - frame_index * 0.05)
    if current_shake <= 0:
        return frame

    offset_x = int(random.uniform(-current_shake, current_shake))
    offset_y = int(random.uniform(-current_shake, current_shake))

    width, height = frame.size
    shaken = Image.new("RGB", (width, height), (30, 30, 30))
    shaken.paste(frame, (offset_x, offset_y))
    return shaken

def create_flash_frame(frame, intensity):
    """Create a flash effect by brightening the frame."""
    if intensity <= 0:
        return frame

    enhancer = ImageEnhance.Brightness(frame)
    return enhancer.enhance(1 + intensity)

def draw_glow_ring(draw, center_x, center_y, radius, color, pulse_phase):
    """Draw a pulsing glow ring around the winning item."""
    pulse = 0.5 + 0.5 * math.sin(pulse_phase)
    glow_radius = radius + int(10 * pulse)

    # Draw multiple rings with decreasing opacity for glow effect
    for i in range(5, 0, -1):
        r = glow_radius + i * 3
        alpha = int(100 * pulse / i)
        glow_color = tuple(min(255, c + alpha) for c in color)
        draw.ellipse(
            (center_x - r, center_y - r, center_x + r, center_y + r),
            outline=glow_color,
            width=2
        )

def extend_gif_with_confetti_and_text(frames, extension_frames, top_text, bottom_text, rarity):
    last_frame = frames[-1]
    width, height = last_frame.size

    config = get_rarity_config(rarity)
    base_color = config["color"]
    num_beams = config["beams"]
    shake_amount = config["shake"]
    flash_intensity = config["flash"]

    density = (15 * rarity) + 5
    center_x, center_y = width // 2, height // 2

    # Create confetti particles with more variety for higher rarities
    confetti = []
    for _ in range(density):
        # Vary starting positions - burst from center
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(4, 12)
        confetti.append({
            "x": center_x,
            "y": center_y + 20,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed - 5,  # Slight upward bias
            "color": generate_similar_color(base_color),
            "size": random.randint(2, 5),
            "rotation": random.uniform(0, 360),
            "rotation_speed": random.uniform(-10, 10),
            "shape": random.choice(["circle", "square", "star"]) if rarity >= 83 else "circle"
        })

    # Add extra glitter particles for epic+ rarities
    if rarity >= 91:
        for _ in range(density // 2):
            confetti.append({
                "x": random.randint(0, width),
                "y": random.randint(0, height),
                "vx": random.uniform(-1, 1),
                "vy": random.uniform(1, 3),
                "color": (255, 255, 255),
                "size": 1,
                "rotation": 0,
                "rotation_speed": 0,
                "shape": "glitter"
            })

    for frame_idx in range(extension_frames):
        confetti_frame = last_frame.copy()
        draw = ImageDraw.Draw(confetti_frame)

        # Draw light beams first (behind everything) for rare+ items
        if num_beams > 0:
            beam_rotation = frame_idx * 0.05  # Slow rotation
            beam_length = 150 + 50 * math.sin(frame_idx * 0.2)  # Pulsing length
            beam_alpha = 0.3 + 0.2 * math.sin(frame_idx * 0.15)
            draw_light_beams(draw, center_x, center_y + 20, num_beams, beam_length, 0.8, base_color, beam_rotation, beam_alpha)

        # Draw pulsing glow ring for epic+ items
        if rarity >= 91:
            pulse_phase = frame_idx * 0.3
            draw_glow_ring(draw, center_x, center_y + 20, 60, base_color, pulse_phase)

        # Update and draw confetti particles
        for particle in confetti:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += 0.25  # Gravity
            particle["vx"] *= 0.99  # Air resistance
            particle["rotation"] += particle["rotation_speed"]

            # Wrap around screen
            particle["x"] %= width
            if particle["y"] > height:
                particle["y"] = -10
                particle["x"] = random.randint(0, width)

            x, y = particle["x"], particle["y"]
            size = particle["size"]
            color = particle["color"]

            if particle["shape"] == "circle":
                draw.ellipse((x - size, y - size, x + size, y + size), fill=color)
            elif particle["shape"] == "square":
                # Rotated square effect
                draw.rectangle((x - size, y - size, x + size, y + size), fill=color)
            elif particle["shape"] == "star":
                # Simple star shape
                draw.polygon([
                    (x, y - size * 2),
                    (x + size * 0.5, y - size * 0.5),
                    (x + size * 2, y),
                    (x + size * 0.5, y + size * 0.5),
                    (x, y + size * 2),
                    (x - size * 0.5, y + size * 0.5),
                    (x - size * 2, y),
                    (x - size * 0.5, y - size * 0.5),
                ], fill=color)
            elif particle["shape"] == "glitter":
                # Twinkling glitter
                if (frame_idx + int(x)) % 3 == 0:
                    draw.point((x, y), fill=(255, 255, 255))
                    draw.point((x + 1, y), fill=(200, 200, 200))
                    draw.point((x, y + 1), fill=(200, 200, 200))

        # Draw sparkles for legendary items
        if rarity >= 97:
            draw_sparkles(draw, width, height, 15, frame_idx, base_color)

        # Draw text with glow effect for higher rarities
        if rarity >= 83:
            # Text shadow/glow
            for offset in [(1, 1), (-1, -1), (1, -1), (-1, 1)]:
                draw.text((width // 2 + offset[0], 12 + offset[1]), top_text, fill=base_color, anchor="mm")
                draw.text((width // 2 + offset[0], height - 28 + offset[1]), bottom_text, fill=base_color, anchor="mm")

        draw.text((width // 2, 12), top_text, fill="white", anchor="mm")
        draw.text((width // 2, height - 28), bottom_text, fill="white", anchor="mm")

        # Apply screen shake for epic+ items (decreasing over time)
        if shake_amount > 0 and frame_idx < 20:
            confetti_frame = apply_screen_shake(confetti_frame, shake_amount, frame_idx)

        # Apply flash effect at the start
        if frame_idx < 5 and flash_intensity > 0:
            flash_power = flash_intensity * (1 - frame_idx / 5)
            confetti_frame = create_flash_frame(confetti_frame, flash_power)

        frames.append(confetti_frame)

    return frames

def create_crate_unboxing_gif(
    images,
    target_index,
    frame_size=(400, 200),
    spin_duration=2,
    fps=17,
    initial_speed_modifier=1.0,
    rarity=50,
):
    num_items = len(images)
    total_frames = int(spin_duration * fps)
    item_spacing = 105
    carousel_width = item_spacing * num_items
    center_x, center_y = frame_size[0] // 2, frame_size[1] // 2

    config = get_rarity_config(rarity)
    highlight_color = config["color"]

    frames = []

    random_offset = random.uniform(0, 1)
    target_offset = (target_index * item_spacing) - (item_spacing * random_offset)

    adjusted_carousel_width = carousel_width * initial_speed_modifier

    # Calculate dramatic pause point (when almost landing)
    dramatic_pause_start = int(total_frames * 0.85)
    dramatic_pause_frames = int(fps * 0.5)  # Half second dramatic pause

    for frame_index in range(total_frames + dramatic_pause_frames):
        # Handle dramatic pause
        if frame_index >= dramatic_pause_start and frame_index < dramatic_pause_start + dramatic_pause_frames:
            # During pause, use the position just before pause started
            effective_frame = dramatic_pause_start
            pause_progress = (frame_index - dramatic_pause_start) / dramatic_pause_frames
        elif frame_index >= dramatic_pause_start + dramatic_pause_frames:
            # After pause, continue from where we left off
            effective_frame = frame_index - dramatic_pause_frames
            pause_progress = 0
        else:
            effective_frame = frame_index
            pause_progress = 0

        progress = effective_frame / total_frames

        # Easing function for smooth deceleration
        if progress < 0.9:
            easing = 2 ** (-10 * progress)
        else:
            easing = 2 ** (-10 * 0.9) * (1 - (progress - 0.9) / 0.1)

        offset = easing * adjusted_carousel_width + (1 - easing) * target_offset

        # Calculate zoom level for dramatic effect near the end
        zoom = 1.0
        if progress > 0.8:
            # Zoom in slightly as we approach the winner
            zoom_progress = (progress - 0.8) / 0.2
            zoom = 1.0 + 0.15 * zoom_progress  # Max 15% zoom

        # During dramatic pause, add pulsing zoom
        if frame_index >= dramatic_pause_start and frame_index < dramatic_pause_start + dramatic_pause_frames:
            pulse = math.sin(pause_progress * math.pi * 3) * 0.05
            zoom += pulse

        # Create frame with potential zoom
        if zoom > 1.0:
            # Create larger frame, then crop/scale
            large_size = (int(frame_size[0] * zoom), int(frame_size[1] * zoom))
            frame = Image.new("RGB", large_size, (30, 30, 30))
            draw = ImageDraw.Draw(frame)
            large_center_x = large_size[0] // 2
            large_center_y = large_size[1] // 2
        else:
            frame = Image.new("RGB", frame_size, (30, 30, 30))
            draw = ImageDraw.Draw(frame)
            large_center_x = center_x
            large_center_y = center_y

        # Draw anticipation effects during dramatic pause
        if frame_index >= dramatic_pause_start and frame_index < dramatic_pause_start + dramatic_pause_frames:
            # Pulsing vignette/glow effect
            pulse_intensity = int(30 * math.sin(pause_progress * math.pi * 4))
            for ring in range(3):
                r = 80 + ring * 20
                ring_color = tuple(max(0, min(255, c + pulse_intensity)) for c in highlight_color)
                draw.ellipse(
                    (large_center_x - r, large_center_y - r + 10, large_center_x + r, large_center_y + r + 10),
                    outline=ring_color + (100,) if len(ring_color) == 3 else ring_color,
                    width=2
                )

        # Draw carousel items
        for i in range(-2, num_items + 2):
            idx = i % num_items
            img_x = large_center_x - (i * item_spacing - offset)
            img_y = large_center_y - 50

            # Highlight the item under the needle
            is_highlighted = (large_center_x - item_spacing) < img_x and img_x < large_center_x

            if is_highlighted:
                # Pulsing highlight during dramatic pause
                if frame_index >= dramatic_pause_start and frame_index < dramatic_pause_start + dramatic_pause_frames:
                    pulse = 3 + int(2 * math.sin(pause_progress * math.pi * 6))
                    glow_color = tuple(min(255, c + 50) for c in highlight_color)
                    draw.rectangle(
                        [img_x - 8, img_y - 8, img_x + 108, img_y + 108],
                        outline=glow_color,
                        width=pulse,
                    )
                draw.rectangle(
                    [img_x - 5, img_y - 5, img_x + 105, img_y + 105],
                    outline=highlight_color,
                    width=3,
                )

            frame.paste(images[idx], (int(img_x), img_y))

        # Draw needle
        needle_x = large_center_x - 5
        draw.polygon(
            [(needle_x, 10), (needle_x + 10, 10), (needle_x + 5, 50)], fill="red"
        )

        # Draw speed lines during fast spinning (early frames)
        if progress < 0.3:
            speed_intensity = int(255 * (0.3 - progress) / 0.3)
            for _ in range(5):
                line_y = random.randint(20, frame_size[1] - 20) if zoom == 1.0 else random.randint(20, large_size[1] - 20)
                line_color = (speed_intensity, speed_intensity, speed_intensity)
                line_width = frame_size[0] if zoom == 1.0 else large_size[0]
                draw.line([(0, line_y), (line_width, line_y)], fill=line_color, width=1)

        # Crop/resize if zoomed
        if zoom > 1.0:
            # Calculate crop box to center on the action
            crop_x = (large_size[0] - frame_size[0]) // 2
            crop_y = (large_size[1] - frame_size[1]) // 2
            frame = frame.crop((crop_x, crop_y, crop_x + frame_size[0], crop_y + frame_size[1]))

        frames.append(frame)

    # Hold on final frame briefly
    for _ in range(int(fps * 0.3)):
        frames.append(frames[-1])

    return frames

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



def generate_gif(thumbnails, win_text, win_rarity, target_index, fps):
    start_time = time.time()
    preprocessed_thumbnails = preprocess_thumbnails_from_urls(thumbnails, thumbnail_size=(100, 100), reduce_colors=True)
    print("--- %s seconds to preprocess thumbnails ---" % (time.time() - start_time))


    start_time = time.time()
    frames = create_crate_unboxing_gif(preprocessed_thumbnails * 16, target_index, spin_duration=5, fps=fps, rarity=win_rarity)
    print("--- %s seconds ---" % (time.time() - start_time))

    top_text = "WINNER!!!"
    bottom_text = win_text
    extension_frames = 5 * fps
    start_time = time.time()
    frames = extend_gif_with_confetti_and_text(frames, extension_frames, top_text, bottom_text, win_rarity)
    print("--- %s seconds ---" % (time.time() - start_time))

    print(len(frames))

    start_time = time.time()
    gif_bytes = parallel_save_gif(frames, duration=int(1000 / fps))
    print("--- %s seconds to save GIF ---" % (time.time() - start_time))
    return gif_bytes


#target_index = 0
#output_path = "crate_unboxing.gif"
#fps = 20
#
#output_path = "crate_unboxing.gif"
#with open(output_path, "wb") as f:
#    f.write(gif_bytes.getvalue())
#print(f"GIF saved to {output_path}")
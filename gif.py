from PIL import Image, ImageDraw
import random
import time
import io
import concurrent.futures
import requests

def extend_gif_with_confetti_and_text(frames, extension_frames, density, top_text, bottom_text, font=None):
    last_frame = frames[-1]
    width, height = last_frame.size

    confetti = [
        {
            "x": width // 2,
            "y": (height // 2)+(height * 0.4),
            "vx": random.uniform(-6, 6),
            "vy": random.uniform(-10, -6),
            "color": (
                random.randint(0, 255), 
                random.randint(0, 255), 
                random.randint(0, 255),
            ),
        }
        for _ in range(density)
    ]

    for _ in range(extension_frames):
        confetti_frame = last_frame.copy()
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

        if font is None:
            draw.text((width // 2, 10), top_text, fill="white", anchor="mm")
            draw.text((width // 2, height - 30), bottom_text, fill="white", anchor="mm")
        else:
            text_width, text_height = draw.textsize(top_text, font=font)
            draw.text(((width - text_width) // 2, 10), top_text, fill="white", font=font)
            text_width, text_height = draw.textsize(bottom_text, font=font)
            draw.text(((width - text_width) // 2, height - text_height - 10), bottom_text, fill="white", font=font)

        frames.append(confetti_frame)

    return frames

def create_crate_unboxing_gif(
    images,
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

            if (center_x - item_spacing) < img_x and img_x < (center_x):
                draw.rectangle(
                    [img_x - 5, img_y - 5, img_x + 105, img_y + 105],
                    outline=highlight_color,
                    width=3,
                )

            frame.paste(images[idx], (int(img_x), img_y))

        needle_x = center_x - 5
        draw.polygon(
            [(needle_x, 10), (needle_x + 10, 10), (needle_x + 5, 50)], fill="red"
        )

        frames.append(frame)

    for _ in range(fps):
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



def generate_gif(thumbnails, target_index, fps):
    start_time = time.time()
    preprocessed_thumbnails = preprocess_thumbnails_from_urls(thumbnails, thumbnail_size=(100, 100), reduce_colors=True)
    print("--- %s seconds to preprocess thumbnails ---" % (time.time() - start_time))


    start_time = time.time()
    frames = create_crate_unboxing_gif(preprocessed_thumbnails * 16, target_index, spin_duration=5, fps=fps)
    print("--- %s seconds ---" % (time.time() - start_time))

    density = 150
    top_text = "WINNER!!!"
    bottom_text = "ROTTE"
    extension_frames = 5 * fps
    start_time = time.time()
    frames = extend_gif_with_confetti_and_text(frames, extension_frames, density, top_text, bottom_text, None)
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
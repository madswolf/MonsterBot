from PIL import Image, ImageDraw
import imageio
import random
import time
import io
import numpy as np
import concurrent.futures
def extend_gif_with_confetti_and_text(frames, extension_frames, density, top_text, bottom_text, font=None):
    """
    Extend a list of GIF frames with an animated confetti effect and static text.

    Parameters:
        frames (list[Image.Image]): List of frames (Pillow Image objects) of the GIF.
        extension_frames (int): Number of frames to add with the confetti effect.
        density (int): Number of confetti particles to generate per frame.
        top_text (str): Text to display at the top of the frame.
        bottom_text (str): Text to display at the bottom of the frame.
        font (ImageFont.ImageFont, optional): Font for the text. Defaults to None (uses default font).

    Returns:
        list[Image.Image]: Extended list of frames with confetti animation and text.
    """
    # Get the last frame and its size
    last_frame = frames[-1]
    width, height = last_frame.size

    # Generate confetti particles
    confetti = [
        {
            "x": width // 2,  # Start from the center
            "y": (height // 2)+(height * 0.4),
            "vx": random.uniform(-6, 6),  # Random horizontal velocity
            "vy": random.uniform(-10, -6),  # Random upward velocity
            "color": (
                random.randint(0, 255), 
                random.randint(0, 255), 
                random.randint(0, 255),
            ),
        }
        for _ in range(density)
    ]

    # Create additional frames with confetti animation
    for _ in range(extension_frames):
        confetti_frame = last_frame.copy()
        draw = ImageDraw.Draw(confetti_frame)

        # Update confetti positions and draw
        for particle in confetti:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += 0.3  # Gravity effect

            # Wrap horizontally and reset vertically
            particle["x"] %= width
            particle["y"] %= height
            

            # Draw the confetti particle
            draw.ellipse(
                (particle["x"] - 2, particle["y"] - 2, particle["x"] + 2, particle["y"] + 2),
                fill=particle["color"]
            )

        # Draw top and bottom text
        if font is None:
            # Use default font if none is provided
            draw.text((width // 2, 10), top_text, fill="white", anchor="mm")
            draw.text((width // 2, height - 30), bottom_text, fill="white", anchor="mm")
        else:
            text_width, text_height = draw.textsize(top_text, font=font)
            draw.text(((width - text_width) // 2, 10), top_text, fill="white", font=font)
            text_width, text_height = draw.textsize(bottom_text, font=font)
            draw.text(((width - text_width) // 2, height - text_height - 10), bottom_text, fill="white", font=font)

        # Append the frame
        frames.append(confetti_frame)

    return frames

def create_crate_unboxing_gif(
    thumbnails,
    target_index,
    frame_size=(400, 200),
    spin_duration=2,
    fps=17,
    initial_speed_modifier=1.0,
):
    """
    Create a crate unboxing GIF in the style of Counter-Strike.

    :param thumbnails: List of file paths to thumbnail images.
    :param target_index: The index of the item to land on.
    :param output_path: The file path to save the resulting GIF.
    :param frame_size: Tuple (width, height) of the GIF frames.
    :param spin_duration: Duration of the spinning animation in seconds.
    :param fps: Frames per second for the GIF.
    :param initial_speed_modifier: Multiplier for the starting speed of the carousel.
    """
    # Load thumbnails as PIL images
    images = [Image.open(path).resize((100, 100)) for path in thumbnails]

    # Carousel parameters
    num_items = len(images)
    total_frames = int(spin_duration * fps)
    item_spacing = 105  # Space between each item in the carousel
    carousel_width = item_spacing * num_items  # Total width of the virtual carousel
    center_x, center_y = frame_size[0] // 2, frame_size[1] // 2
    highlight_color = (255, 215, 0)

    # Placeholder for frames
    frames = []

    random_offset = random.uniform(0,1)
    # Calculate the final stop position for the target
    target_offset = (target_index * item_spacing) + (item_spacing * random_offset)

    # Adjust carousel width based on initial speed modifier
    adjusted_carousel_width = carousel_width * initial_speed_modifier
    
    # Randomly select a stopping point within the target item

    # Generate the animation
    for frame_index in range(total_frames):
        # Compute how far the carousel has moved
        progress = frame_index / total_frames

        if progress < 0.9:
            easing = 2 ** (-10 * progress)
        else:
            # Linear interpolation from the last easing value at progress=0.9 to 0
            easing = 2 ** (-10 * 0.9) * (1 - (progress - 0.9) / 0.1)

        # Stop randomly inside the target area
        offset = easing * adjusted_carousel_width + (1 - easing) * target_offset

        # Create a new frame
        frame = Image.new("RGB", frame_size, (30, 30, 30))
        draw = ImageDraw.Draw(frame)

        # Draw carousel
        for i in range(-2, num_items + 2):  # Display extra items to cover wrap-around
            idx = i % num_items
            img_x = center_x + (i * item_spacing - offset)
            img_y = center_y - 50

            # Highlight the target item if it's centered
            if (center_x - item_spacing) < img_x and img_x < (center_x):
                draw.rectangle(
                    [img_x - 5, img_y - 5, img_x + 105, img_y + 105],
                    outline=highlight_color,
                    width=3,
                )

            frame.paste(images[idx], (int(img_x), img_y))

        # Add the needle
        needle_x = center_x - 5
        draw.polygon(
            [(needle_x, 10), (needle_x + 10, 10), (needle_x + 5, 50)], fill="red"
        )

        frames.append(frame)

    # Extend the final frame for a pause effect
    for _ in range(fps):
        frames.append(frames[-1])

    return frames



def encode_frame_to_bytes(frame, duration):
    """
    Encode a single frame to a GIF-compatible byte stream.

    Parameters:
        frame (Image.Image): The frame to encode.
        duration (int): Duration of the frame in milliseconds.

    Returns:
        bytes: Encoded frame as a byte stream.
    """
    frame_bytes = io.BytesIO()
    frame.save(frame_bytes, format="GIF", duration=duration)
    return frame_bytes.getvalue()


def assemble_gif_from_encoded_frames(encoded_frames, duration=50):
    """
    Assemble a GIF from a list of pre-encoded frame byte streams.

    Parameters:
        encoded_frames (list[bytes]): List of byte streams for each frame.
        duration (int): Duration for each frame in milliseconds.

    Returns:
        io.BytesIO: In-memory bytes object containing the GIF data.
    """
    gif_buffer = io.BytesIO()

    # Load the first frame as the base
    first_frame = Image.open(io.BytesIO(encoded_frames[0]))
    rest_frames = [Image.open(io.BytesIO(f)) for f in encoded_frames[1:]]

    # Save the GIF
    first_frame.save(
        gif_buffer,
        format="GIF",
        save_all=True,
        append_images=rest_frames,
        duration=duration,
        loop=0,
        optimize=False,
    )

    gif_buffer.seek(0)  # Reset buffer position
    return gif_buffer


def parallel_save_gif(frames, duration=50):
    """
    Save a sequence of frames as a GIF in parallel.

    Parameters:
        frames (list[Image.Image]): List of frames to save as a GIF.
        duration (int): Duration for each frame in milliseconds.

    Returns:
        io.BytesIO: In-memory bytes object containing the GIF data.
    """
    # Encode frames in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        encoded_frames = list(
            executor.map(encode_frame_to_bytes, frames, [duration] * len(frames))
        )

    # Assemble the final GIF from encoded frames
    return assemble_gif_from_encoded_frames(encoded_frames, duration)


# Example usage
thumbnails = ["1.jpg", "2.jpg", "3.jpg", "4.jpg"] * 19
target_index = 3
output_path = "crate_unboxing.gif"
fps = 20

start_time = time.time()
frames = create_crate_unboxing_gif(thumbnails, target_index, spin_duration=5, fps=fps)
print("--- %s seconds ---" % (time.time() - start_time))

#density = 250
#top_text = "WINNER!!!"
#bottom_text = "ROTTE"
#extension_frames = 5 * fps
#start_time = time.time()
#frames = extend_gif_with_confetti_and_text(frames, extension_frames, density, top_text, bottom_text, None)
#print("--- %s seconds ---" % (time.time() - start_time))

print(len(frames))

# Save GIF to in-memory buffer
start_time = time.time()
gif_bytes = parallel_save_gif(frames, duration=int(1000 / fps))
print("--- %s seconds to save GIF ---" % (time.time() - start_time))

# Example: Write to file if needed
output_path = "crate_unboxing.gif"
with open(output_path, "wb") as f:
    f.write(gif_bytes.getvalue())
print(f"GIF saved to {output_path}")
from PIL import Image, ImageDraw
import imageio
import random

def create_crate_unboxing_gif(
    thumbnails,
    target_index,
    output_path,
    frame_size=(400, 200),
    spin_duration=2,
    fps=30,
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

            if 0 <= img_x <= frame_size[0]:  # Only draw items visible on the frame
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

    # Save as GIF
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / fps),
        loop=0,  # Loop 0 times (no repetition)
    )

    print(f"GIF saved to {output_path}")


# Example usage
thumbnails = [ "1.jpg", "2.jpg", "3.jpg", "4.jpg"] * 19
target_index = 1
create_crate_unboxing_gif(thumbnails, target_index, "crate_unboxing.gif", spin_duration=6)

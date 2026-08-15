import sys

import pyperclip


def make_single_line_header(title: str, width: int = 88) -> str:
    """Create a single-line 80-column header with the title centered between '='."""
    title = title.strip()
    if not title:
        return ""

    # Subtract 2 for the initial '# ' at the start
    available_width = width - 2

    # Reserve 2 spaces around the title
    total_padding = available_width - len(title) - 2
    if total_padding < 0:
        # Title too long, truncate
        title = title[: available_width - 3] + "..."
        total_padding = available_width - len(title) - 2

    left_padding = total_padding // 2
    right_padding = total_padding - left_padding

    return f"# {'=' * left_padding} {title} {'=' * right_padding}"


def main() -> None:
    # Prompt user for header
    title = " ".join(sys.argv[1:])
    if not title:
        print("No header provided!")
        return

    header = make_single_line_header(title)

    # Copy to clipboard
    pyperclip.copy(header)

    # Print the header
    print("\nGenerated header (copied to clipboard):")
    print(header)


if __name__ == "__main__":
    main()
    main()

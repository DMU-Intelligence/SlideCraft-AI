# PPTX Generator MCP Server

This MCP server exposes `python-pptx` library functions as tools for the Gemini CLI.

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the server using stdio:
```bash
python server.py
```

## Tools

- `create_presentation(width_inches, height_inches)`: Initializes a new PPTX.
- `add_slide(presentation_id, layout_index)`: Adds a slide (default 6 is blank).
- `set_slide_background(presentation_id, slide_index, hex_color)`: Sets background color.
- `add_text_box(...)`: Adds a text box with custom font and alignment.
- `add_shape(...)`: Adds a rectangle shape.
- `add_bullet_list(...)`: Adds a bulleted list.
- `save_presentation(presentation_id, filename)`: Saves the result to the `output/` directory.

## Gemini CLI Configuration

Add the following to your Gemini CLI configuration (e.g., in `config.yaml` or through the CLI interface):

```yaml
mcpServers:
  pptx:
    command: python
    args: ["C:/Users/Tmforl/Desktop/고급인공지능/project/mcp/server.py"]
    env:
      PYTHONPATH: "C:/Users/Tmforl/Desktop/고급인공지능/project/mcp"
```
*(Note: Adjust the paths to be absolute paths on your system)*

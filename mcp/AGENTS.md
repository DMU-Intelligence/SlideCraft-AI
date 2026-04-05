# PPTX Generation Workflow

When a user asks to generate a presentation from a file (e.g., PDF), you (the LLM agent) must handle the intelligence and orchestration. The MCP server provides ONLY raw PPTX manipulation tools.

## Workflow:
1. **Extract**: Use your local file reading tools (like `read_file` or `run_shell_command` with a pdf reader) to read the user's PDF.
2. **Summarize & Outline**: Use YOUR OWN intelligence (Gemini) to summarize the text and plan the slide titles and bullet points. Do this in your thought process.
3. **Build PPTX**: 
   - Call `create_presentation` to get a `presentation_id`.
   - For each planned slide:
     - Call `add_slide`
     - Call `add_text_box` for the title
     - Call `add_bullet_list` for the content
   - Finally, call `save_presentation`.

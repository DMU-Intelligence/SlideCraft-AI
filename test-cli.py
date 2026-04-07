import subprocess
import os

def run_gemini_cli(prompt_text: str):
    cmd = os.getenv("GEMINI_CLI_COMMAND", "gemini")
    full_prompt = (
        f"""Return only valid JSON. No explanation, no markdown fences.

{prompt_text}"""
    )

    print(f"Executing: cmd.exe /c {cmd}")
    print(f"Sending prompt to Gemini CLI: {prompt_text[:100]}...")

    try:
        result = subprocess.run(
            ['cmd.exe', '/c', cmd],
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300,
            check=False # Do not raise CalledProcessError automatically
        )

        if result.returncode != 0:
            print(f"Error: CLI returned non-zero exit code {result.returncode}")
            print(f"Stdout: {(result.stdout or '')}")
            print(f"Stderr: {(result.stderr or '')}")
        else:
            print("Gemini CLI Response:")
            print(result.stdout.strip())

    except FileNotFoundError:
        print(f"Error: The command '{cmd}' was not found. "
              f"Ensure GEMINI_CLI_COMMAND is set correctly or 'gemini' is in PATH.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_gemini_cli("hello")

import re
import sys


def extract():
    try:
        with open("server.mjs", "r") as f:
            content = f.read()

            target = "customGitUrl"
            idx = content.find(target)
            if idx != -1:
                print(f"--- Found '{target}' at offset {idx} ---")
                start = max(0, idx - 1000)
                end = min(len(content), idx + 3000)
                print(f"Context:\n{content[start:end]}")
            else:
                print(f"Could not find '{target}'")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    extract()

import base64
import pyautogui
import pyttsx3
import time
import os
from openai import OpenAI
from pynput import keyboard

# Configuration export OPENAI_API_KEY='your-key'
API_KEY = os.getenv("OPENAI_API_KEY")  
TEMP_IMAGE = "current_page.png"
DEFAULT_SPEED = 175
VOICE_INDEX = 1
MAX_HISTORY = 5  # Maximum context entries to retain
TEXT_FILE = "total_book_text.txt"

# Global states
exit_flag = False

# Stores last MAX_HISTORY entries
text_history = []  

# Initialize OpenAI client
client = OpenAI(api_key=API_KEY)

#  Capture screen with stabilization delay
def take_screenshot():
    time.sleep(0.3)  # Reduces capture artifacts
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(TEMP_IMAGE)
        return TEMP_IMAGE
    except Exception as e:
        print(f"Screenshot error: {str(e)}")
        return None

# Extract text using previous context
def extract_text_with_history(image_path):
    global text_history
    
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        # Build context-aware prompt
        history_context = "\n".join(text_history[-MAX_HISTORY:])
        system_prompt = (
                f"Previous context:\n{history_context}\n\n"
                "Extract ALL text verbatim with 100% completeness. "
                "If text continues past visible area, indicate with '[...]'. "
                "NO SUMMARIZATION. NO OMISSIONS. INCLUDE PARTIAL LINES."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]}
            ],
            temperature=0.3,
            max_tokens=7000
        )
        
        new_text = response.choices[0].message.content.strip()
        
        # Update history and save
        text_history.append(new_text)
        if len(text_history) > MAX_HISTORY:
            text_history.pop(0)
            
        save_total_text(new_text)
        return new_text
        
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return None

# Append new text to cumulative file
def save_total_text(new_text):
    try:
        with open(TEXT_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n\n{new_text}")
    except Exception as e:
        print(f"Save error: {str(e)}")

# Convert text to speech with validation
def text_to_speech(text):
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        # Validate voice index
        if VOICE_INDEX >= len(voices):
            print(f"Invalid voice index {VOICE_INDEX}, using default")
            engine.setProperty('voice', voices[0].id)
        else:
            engine.setProperty('voice', voices[VOICE_INDEX].id)
            
        engine.setProperty('rate', DEFAULT_SPEED)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Error: {str(e)}")

#  Process current page with history
def on_activate():
    print("Processing page...")
    if (image_path := take_screenshot()):
        if (text_content := extract_text_with_history(image_path)):
            text_to_speech(text_content)
            print(f"Page processed (History: {len(text_history)}/{MAX_HISTORY})")
        else:
            print("Text extraction failed")
    else:
        print("Capture failed")

def exit_program():
    global exit_flag
    exit_flag = True
    print("\nExiting...")

def main():
    print(f"""Book Reader AI Active
- Hotkey: CTRL+SHIFT+\\ Process page
- Hotkey: CTRL+SHIFT+Q Quit
- History: Last {MAX_HISTORY} pages
- Text saved to: {TEXT_FILE}""")

    with keyboard.GlobalHotKeys({
            '<ctrl>+<shift>+\\': on_activate,
            '<ctrl>+<shift>+q': exit_program
        }) as listener:
        while not exit_flag:
            time.sleep(0.5)
            
    print("Cleaning up...")
    if os.path.exists(TEMP_IMAGE):
        os.remove(TEMP_IMAGE)

if __name__ == "__main__":
    main()

import os
import json
import requests
from moviepy.editor import ImageClip, concatenate_audioclips, AudioFileClip, TextClip, CompositeVideoClip

def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

print("Starting video generation script...")

# Replace with your actual API endpoints and data
image_api_url = "https://us-central1-chat-window-widget.cloudfunctions.net/gpt-dalle-request"
gpt_api_url = "https://us-central1-chat-window-widget.cloudfunctions.net/gpt-ai-request"
# tts_api_url = "https://us-central1-chat-window-widget.cloudfunctions.net/google-tts"
tts_api_url = "https://us-central1-chat-window-widget.cloudfunctions.net/eleven-labs-tts"

text = "Overcoming the loss of a loved one"

print("Generating gpt response...")

# Get subtitles
gpt_response = requests.post(gpt_api_url, json={
    'systemMessage':
    "Treat the user's message as a topic. Create a good relatable passage from the Bible about the topic provided by the user, the passage should begin with \"bible passage - start\" and at  the end, it should read \"bible passage - end\" (excluding quote marks), these will be my delimiters for my code. Next give a description of the passage in words separated by commas. These will be adjectives, nouns, verbs, that describe the feelings and emotions of this passage to an image generation software. Delimit this with \"image prompt - start\" and delimit the end with \"image prompt - end\" (excluding quote marks). Next, give a paragraph (that would take about 45 seconds for a calm voice to read fully) , that has same meaning, is inspirational or motivational, that relates to a daily life of an average person - the inspirational paragraph should being with \"inspirational - start\" and at the end of it, please output \"inspirational - end\" (excluding quote marks). These will be my delimiters .  Before this inspirational paragraph, (that I'm going to put it into a video with ambient music, for people to listen to) can you give me something to say as an introduction before that quote, to greet people and that them for being with us and taking their time to listen - delimit the start with \"intro - start\", and delimit the end with \"intro - end\" (excluding quote marks). And give me something to say in the end, after the quote, to tell them good bye, thanks again, and please enjoy this beautiful ambient music i've made, hopefully to make your day better - delimit the start of this with \"conclusion - start\" and delimit the end of this with \"conclusion - end\" (excluding quote marks). And then turn it (The intro, the bible passage, the inspirational paragraph, and the conclusion together (do not include delimiters in the subtitles array)) into a set of subtitles in array format. Ensure the subtitles, completely read the passage created verbatim.  But be sure to output the whole passage. And then its corresponding array. Be sure to output the array following the characters \"Subtitles Array: \" (excluding quote marks) every time. And the array should be of form [\"subtitle1\", \"subtitle2\", \"subtitle3\", etc…]. No item in the subtitle array should be longer than 13 words. Be sure there are no further characters after the last subtitle in the array.",
    'aiModel': "gpt-4",
    'messages': [{'role': "user", 'content': text}],
})

response_json = gpt_response.json()
message = response_json.get('message', '')
print(f"Response Content: {message}")

# Extracting the specific string for image prompt
start_marker = "image prompt - start"
end_marker = "image prompt - end"
start_index = message.find(start_marker)
end_index = message.find(end_marker)

if start_index != -1 and end_index != -1:
    image_prompt = message[start_index + len(start_marker):end_index].strip()
else:
    image_prompt = ""
    print("Image prompt not found in the response")

# Concatenate with additional text
full_image_prompt = "bible, religion friendly image, " + image_prompt

print("Requesting image generation with prompt:", full_image_prompt)

# Make the image API call
image_response = requests.post(image_api_url, json={'prompt': full_image_prompt})

if image_response.status_code == 200:
    image_url = image_response.json().get('imageUrl')
    print(f"Image URL received: {image_url}")
    image_clip = ImageClip(image_url, duration=10)  # Duration is an example
else:
    print(f"Error in image API call: Status Code {image_response.status_code}")
    print(f"Response Content: {image_response.text}")

print(f"Response Content: {image_response.text}")
print("Requesting TTS audio for the subtitle array...")
start_index = message.find("Subtitles Array:")
if start_index != -1:
    # Extract the array part from the message
    array_str = message[start_index + len("Subtitles Array:"):].strip()
    try:
        # Parse the string as a JSON array
        subtitles = json.loads(array_str)
    except json.JSONDecodeError:
        print("Error decoding the subtitles array")
        subtitles = []
else:
    print("Subtitles Array not found in the response")
    subtitles = []

print(f"Subtitles received: {subtitles}")


print("Fetching TTS audio for each subtitle...")

audio_clips = []
text_clips = []
total_duration = 0

print("Concatenating subtitles for TTS...")
print(f"Subtitles: {subtitles}")
concatenated_subtitles = ' '.join(subtitles)
print(f"Concatenated Subtitles: {concatenated_subtitles}")

# Send the concatenated subtitles to TTS and download the audio file
tts_response = requests.post(tts_api_url, json={'text': concatenated_subtitles})
if tts_response.status_code == 200:
    tts_url = tts_response.json().get('audioUrl')
    local_audio_filename = "complete_audio.mp3"
    download_file(tts_url, local_audio_filename)
    final_audio = AudioFileClip(local_audio_filename)
else:
    print(f"Error in TTS API call: Status Code {tts_response.status_code}")
    print(f"Response Content: {tts_response.text}")
    # Handle the error appropriately

# Create TextClips and sync with the audio
text_clips = []
total_duration = final_audio.duration
current_start = 0

for subtitle in subtitles:
    # Estimate duration of each subtitle (simple approach based on number of words)
    subtitle_duration = len(subtitle.split()) / len(concatenated_subtitles.split()) * total_duration
    
    text_clip = TextClip(subtitle, fontsize=35, color='white', font='Arial', align='center')
    text_clip = text_clip.set_duration(subtitle_duration)
    text_clip = text_clip.set_start(current_start)
    text_clip = text_clip.set_position(('center', 'bottom'))
    text_clip = text_clip.margin(bottom=20, opacity=0)
    text_clips.append(text_clip)

    current_start += subtitle_duration


# Concatenate audio clips
# final_audio = concatenate_audioclips(audio_clips) 

# Update the duration of the image clip to match the total duration of the audio
image_clip = image_clip.set_duration(total_duration)

# Composite the text clips onto the image clip
final_video = CompositeVideoClip([image_clip] + text_clips, size=image_clip.size)

# Set audio to the composite video clip
final_video = final_video.set_audio(final_audio)

# Write the result to a file
final_video.fps = 24
print("Writing the result to a file...")
final_video.write_videofile("output.mp4", audio_codec='aac', fps=final_video.fps)

print("Video generation completed. Check 'output.mp4'.")
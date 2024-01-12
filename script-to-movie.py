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
subtitles_api_url = "https://us-central1-chat-window-widget.cloudfunctions.net/gpt-ai-request"
tts_api_url = "https://us-central1-chat-window-widget.cloudfunctions.net/google-tts"
# tts_api_url = "https://us-central1-chat-window-widget.cloudfunctions.net/eleven-labs-tts"

timeout_duration = 180

text = "what is the meaning of life?"
print("Requesting image generation...")

try:
    image_response = requests.post(image_api_url, timeout=timeout_duration, json={'prompt': text})

    if image_response.status_code == 200:
        image_url = image_response.json().get('imageUrl')
        print(f"Image URL received: {image_url}")
        image_clip = ImageClip(image_url, duration=10) # Duration is an example

        print("Generating subtitles...")

        # Get subtitles
        subtitles_response = requests.post(subtitles_api_url, timeout=timeout_duration, json={
            'systemMessage':
            "The user is attempting to make a still image movie given the passage provided. Create a good relatable passage from the Bible about the topic provided by the user, the passage should begin with \"bible passage - start\" and at  the end, it should read \"bible passage - end\", these will be my delimiters for my code. Next give a description of the passage in words separated by commas. These will be adjectives, nouns, verbs, that describe the feelings and emotions of this passage to an image generation software. Delimit this with \"image prompt - start\" and delimit the end with \"image prompt - end\". Next, give a paragraph (that would take about 45 seconds for a calm voice to read fully) , that has same meaning, is inspirational or motivational, that relates to a daily life of an average person - the inspirational paragraph should being with \"inspirational - start\" and at the end of it, please output \"inspirational - end\". These will be my delimiters .  Before this inspirational paragraph, (that I'm going to put it into a video with ambient music, for people to listen to) can you give me something to say as an introduction before that quote, to greet people and that them for being with us and taking their time to listen - delimit the start with \"intro - start\", and delimit the end with \"intro - end\" . And give me something to say in the end, after the quote, to tell them good bye, thanks again, and please enjoy this beautiful ambient music i've made, hopefully to make your day better - delimit the start of this with \"conclusion - start\" and delimit the end of this with \"conclusion - end\" . And then turn it (The intro, the bible passage, the inspirational paragraph, and the conclusion together (do not include delimiters in the subtitles array)) into a set of subtitles in array format. Ensure the subtitles, completely read the passage created verbatim.  But be sure to output the whole passage. And then its corresponding array. Be sure to output the array following the characters \"Subtitles Array: \" every time. And the array should be of form [\"subtitle1\", \"subtitle2\", \"subtitle3\", etc...]. Be sure there are no further characters after the last subtitle in the array.",
            'aiModel': "gpt-4",
            'messages': [{'role': "user", 'content': text}],
        })

        response_json = subtitles_response.json()

        # CHANGE: Extracting subtitles from the response message
        message = response_json.get('message', '')
        print(f"Message received: {message}")
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

        for index, subtitle in enumerate(subtitles):
            tts_response = requests.post(tts_api_url, timeout=timeout_duration, json={'text': subtitle})
            tts_url = tts_response.json().get('audioUrl')
            print(f"Fetching TTS audio from: {tts_url}")

            # Download the audio file
            local_audio_filename = f"audio_{index}.mp3"
            download_file(tts_url, local_audio_filename)

            # Create an AudioFileClip and append it to the audio_clips list
            audio_clip = AudioFileClip(local_audio_filename)
            audio_clips.append(audio_clip)

            # Create a TextClip for each subtitle
            text_clip = (TextClip(subtitle, fontsize=35, color='white', font='Arial', align='center')
                        .set_duration(audio_clip.duration)
                        .set_start(total_duration)
                        .set_position(('center', 'bottom'))  # Adjust position here
                        .margin(bottom=20, opacity=0)  # Add padding at the bottom
                        .crossfadein(0.5)  # Fade in effect
                        .crossfadeout(0.5))  # Fade out effect
            text_clips.append(text_clip)

            total_duration += audio_clip.duration

    # Concatenate audio clips
        final_audio = concatenate_audioclips(audio_clips) 

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
    else:
        # Log error details if the response was not successful
        print(f"Error in image API call: Status Code {image_response.status_code}")
        print(f"Response Content: {image_response.text}")
        # Handle error appropriately (e.g., exit script, retry, etc.)

except requests.exceptions.RequestException as e:
    # Log the exception details
    print(f"Exception occurred during image API call: {str(e)}")
    # Handle exception appropriately (e.g., exit script, retry, etc.)
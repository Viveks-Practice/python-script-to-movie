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

text = "A comic book scene describing the battle between zeus and hades of the underworld"
print("Requesting image generation...")
image_response = requests.post(image_api_url, json={'prompt': text})

if image_response.status_code == 200:
    image_url = image_response.json().get('imageUrl')
    print(f"Image URL received: {image_url}")
    image_clip = ImageClip(image_url, duration=10) # Duration is an example

    print("Generating subtitles...")

    # Get subtitles
    subtitles_response = requests.post(subtitles_api_url, json={
        'systemMessage':
          "The user is attempting to make a still image movie given the passage provided. If a movie script were to be made for this passage, and then turned into a set (possibly just one) of subtitles that can be placed over an image that depicts this scene, what would that set of subtitles be? write it in quotes, and provide it as an array. Be strict with what you return, ensure it is just an array response with a series of subtitles that would go well in sequence over a still image that would be depicting the scene provided by the passage. My intent is to show each item in the array one at a time overlaid on the image, so as to speak the movie script / story to the image/passage in question. But be sure to just output the array.",
        'aiModel': "gpt-4",
        'messages': [{ 'role': "user", 'content': text }],
      })
    response_json = subtitles_response.json()
    subtitles = json.loads(response_json.get('message', '[]'))

    print(f"Subtitles received: {subtitles}")

    print("Fetching TTS audio for each subtitle...")

    audio_clips = []
    text_clips = []
    total_duration = 0

    for index, subtitle in enumerate(subtitles):
        tts_response = requests.post(tts_api_url, json={'text': subtitle})
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
    final_video.write_videofile("output.mp4", fps=final_video.fps)

    print("Video generation completed. Check 'output.mp4'.")
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

SCOPES = "user-modify-playback-state user-read-playback-state"

def get_spotify_client():
    """Initializes the secure OAuth user token loop with Spotify servers."""
    try:
        return spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPES))
    except Exception as e:
        print(f"[SPOTIFY ERROR] Authorization handshake failed: {e}")
        return None

def get_target_device_id(sp):
    """Scans your account for an active or open Spotify application."""
    try:
        devices_data = sp.devices().get("devices", [])
        if not devices_data:
            return None
            
        # 1. Look for a device that is currently active first
        for d in devices_data:
            if d.get("is_active"):
                return d.get("id")
                
        # 2. If none are active, grab the ID of the first device in the list
        return devices_data[0].get("id")
    except Exception as err:
        print(f"[DEVICE LOOKUP ERR] {err}")
        return None

def handle_music_command(command_text):
    """Parses spoken keywords passed from brain.py to execute music controls."""
    sp = get_spotify_client()
    if not sp:
        return "Music systems are offline, sir."

    cmd = command_text.lower().strip()
    device_id = get_target_device_id(sp)

    try:
        # --- PAUSE TRACK ---
        if "pause" in cmd or "stop the music" in cmd:
            sp.pause_playback(device_id=device_id)
            return "Music paused, sir."

        # --- RESUME TRACK ---
        elif "resume" in cmd or "play music" in cmd:
            sp.start_playback(device_id=device_id)
            return "Resuming your audio queue, sir."

        # --- SKIP TRACK ---
        elif "next song" in cmd or "skip" in cmd:
            sp.next_track(device_id=device_id)
            return "Skipping to the next track, sir."

        # --- SEARCH & PLAY TRACK ---
        elif "play" in cmd:
            search_query = cmd.split("play")[-1].strip()
            if search_query:
                results = sp.search(q=search_query, limit=1, type="track")
                tracks = results.get("tracks", {}).get("items", [])
                
                if tracks:
                    # FIX: Correctly extract keys from the first item index [0] of the list
                    track_uri = tracks[0].get("uri")
                    track_name = tracks[0].get("name")
                    artist_name = tracks[0]["artists"][0].get("name")
                    
                    sp.start_playback(device_id=device_id, uris=[track_uri])
                    return f"Playing {track_name} by {artist_name}, sir."
                
                return f"I couldn't find any tracks matching '{search_query}' on Spotify."
                
    except Exception as e:
        print(f"[SPOTIFY EXECUTION ERROR] {e}")
        return "I can't see your player, sir. Please play a track on your app manually to link us."

    return "Music query unmapped."

#!/usr/bin/env python3
try:
    from sdl2 import *
    from sdl2.ext import Resources
    from sdl2.ext.compat import byteify
    from sdl2.sdlmixer import *
    # import os
except ImportError:
    import traceback

    traceback.print_exc()
    # os.sys.exit(1)

RESOURCES = Resources(__file__, "sounds")

if SDL_Init(SDL_INIT_AUDIO) != 0:
    raise RuntimeError("Cannot initialize audio system: {}".format(SDL_GetError()))

if Mix_OpenAudio(44100, MIX_DEFAULT_FORMAT, 2, 1024):
    raise RuntimeError("Cannot open mixed audio: {}".format(Mix_GetError()))

sound_file = RESOURCES.get_path("airhorn.wav")
sample = Mix_LoadWAV(byteify(sound_file, "utf-8"))
if sample is None:
    raise RuntimeError("Cannot open audio file: {}".format(Mix_GetError()))
channel = Mix_PlayChannel(-1, sample, 0)
if channel == -1:
    raise RuntimeError("Cannot play sample: {}".format(Mix_GetError()))

while Mix_Playing(channel):
    SDL_Delay(100)

Mix_CloseAudio()
SDL_Quit(SDL_INIT_AUDIO)

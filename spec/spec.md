GIVEN I have Divoom TimeboxEvo. 16x16 pixel grid, bluetooth speaker. No WIFI.
and I need a library which can connect to this device.
Like: https://pypi.org/project/divoom-protocol/ ?

I want to create a Docker webservice which connect to Gemini 3.5 Flash, on global, for GCP Project leeboonstra. The prompt ask for the generation of a 16x16 grid image:

```
prompt = f"""
You are an expert retro video game pixel artist known for unique, stylized, and dynamic 16x16 canvas art. Generate a unique, creative 16x16 pixel art image array representing: "{chosen_theme}".

Output MUST be a valid JSON 2D array containing exactly 16 sub-arrays, each containing exactly 16 RGB lists, structured precisely like this:
[[[r,g,b], [r,g,b], ...], ...]

ARTISTIC RULES:
1. ICONIC FIDELITY: The subject must be instantly recognizable. Do not change canonical/iconic identity colors (e.g., Mario must wear red/blue, Sonic must be blue).
2. COMPOSITIONAL CREATIVITY: Present the subject creatively. Try action poses, dynamic angles, or close-ups instead of a flat flat portrait.
3. BACKGROUNDS: Use creative colors, styling, or shading in the negative space to make the character pop on a physical LED display.
"""
```

and then we need to push that to the device.
The Docker, would also have a cron service, which reruns the script to create a new pixel grid image every 15min. - We should store the previous images, as json files in a folder, /app/downloads
with the timestamp as the name of the file.

I made a try script in the src folder, but i am not so sure if the divoom library is available on pip.

Please create the docker package and the script for my experiment. - I would love to test it out, first as a json grid for me to read. And then as a json grid to push to the actual device, which is available over bluetooth.

Eventually I will run this docker container on my raspberry pi on my network, which uses casaos.
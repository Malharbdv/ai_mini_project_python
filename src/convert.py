import argparse
import os
from music21 import converter, midi

import re
from music21 import stream, note, chord, meter, pitch

def parse_meter(meter_str):
    match = re.search(r'\\meter<"(\d+)/(\d+)">', meter_str)
    return (int(match.group(1)), int(match.group(2))) if match else (4, 4)

def parse_note(token):
    match = re.match(r'([a-gA-G])([#b&]*)(\d)/(\d+)', token)
    if not match:
        raise ValueError(f"Invalid note token: {token}")
    name, accidental, octave, duration = match.groups()
    step = name.upper()
    alter = accidental.count('#') - accidental.count('b') - accidental.count('&')
    dur = 1 / int(duration)
    p = pitch.Pitch(step + octave)
    p.octave = int(octave)
    p.microtone = alter * 100
    return note.Note(p, quarterLength=dur)

def parse_chord(token):
    token = token.strip('{}')
    notes = []
    for n in token.split(','):
        notes.append(parse_note(n.strip()))
    durations = [n.quarterLength for n in notes]
    if len(set(durations)) != 1:
        raise ValueError("Chord notes must have same duration.")
    return chord.Chord(notes, quarterLength=durations[0])

def parse_block(text):
    text = text.strip('{} \n')
    measures = re.findall(r'\[.*?\]', text, re.DOTALL)
    s = stream.Score()
    p = stream.Part()
    for m_text in measures:
        ts = parse_meter(m_text)
        m = stream.Measure()
        m.timeSignature = meter.TimeSignature(f"{ts[0]}/{ts[1]}")
        content = re.sub(r'\\meter<"\d+/\d+">', '', m_text)
        tokens = re.findall(r'\{[^}]+\}|\w+#?\w*&&?\d+/\d+|\w+#?\w*\d+/\d+', content)
        for t in tokens:
            if t.startswith('{'):
                m.append(parse_chord(t))
            else:
                m.append(parse_note(t))
        p.append(m)
    s.append(p)
    return s

def convert_to_xml():
    music_text = 0
    score = parse_block(music_text)
    score.write('musicxml', fp='output.xml')


def process_mxl_file(input_file, input_dir, output_dir):
    try:
        print(f"processing: {input_file}")
        score = converter.parse(input_file)

        relative_path = os.path.relpath(os.path.dirname(input_file), input_dir)
        specific_output_dir = os.path.join(output_dir, relative_path)

        os.makedirs(specific_output_dir, exist_ok=True)

        file_name = os.path.splitext(os.path.basename(input_file))[0]
        midi_path = os.path.join(specific_output_dir, f"{file_name}.mid")

        combined_midi = midi.MidiFile()

        for part in score.parts:
            mf = midi.translate.streamToMidiFile(part)
            for track in mf.tracks:
                combined_midi.tracks.append(track)

        combined_midi.open(midi_path, 'wb')
        combined_midi.write()
        combined_midi.close()

    except Exception as e:
        print(f"Error processing {input_file}: {e}")

def convert_to_midi(input_dir, output_dir):

    input_dir_abs = os.path.abspath(input_dir)
    output_dir_abs = os.path.abspath(output_dir)

    if output_dir_abs.startswith(input_dir_abs):
        print("Output directory cannot be inside the input directory.")
        return

    print(f"Input Directory: {input_dir_abs}")
    print(f"Output Directory: {output_dir_abs}")

    supported_extensions = (".musicxml", ".xml", ".mxl")
    for root, _, files in os.walk(input_dir_abs):
        if output_dir_abs.startswith(root):
            continue

        for file in files:
            if file.lower().endswith(supported_extensions):
                input_file = os.path.join(root, file)
                process_mxl_file(input_file, input_dir_abs, output_dir_abs)

convert_to_midi("input", "output")
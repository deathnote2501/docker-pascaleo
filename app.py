import os
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
import streamlit as st

from pydub.utils import which
AudioSegment.ffmpeg = which("ffmpeg")

# Obtenir la clé API OpenAI à partir d'une variable d'environnement
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("Erreur : la clé API OpenAI n'est pas définie. Veuillez configurer la variable d'environnement OPENAI_API_KEY.")

try:
    # Créer une instance du client OpenAI avec la clé API
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"Erreur lors de la création du client OpenAI : {str(e)}")

# Streamlit interface
st.title("Pascaleo - Retranscription textuelle des entretiens visios")
st.markdown("<hr>", unsafe_allow_html=True)
st.subheader("Entrez les termes techniques issus du GPTs #4 :")
whisper_prompt = st.text_area("", "")
st.markdown("<hr>", unsafe_allow_html=True)
st.subheader("Téléversez vos fichiers MP3 :")
uploaded_files = st.file_uploader("", type="mp3", accept_multiple_files=True)
st.markdown("<hr>", unsafe_allow_html=True)

if st.button("Retranscrire les MP3 en texte"):
    if uploaded_files:
        try:
            total_files = len(uploaded_files)
            for index, uploaded_file in enumerate(uploaded_files):
                # Essayer de sauvegarder le fichier téléversé dans un emplacement temporaire
                try:
                    temp_input_path = f"/tmp/{uploaded_file.name}"
                    with open(temp_input_path, "wb") as temp_file:
                        temp_file.write(uploaded_file.getbuffer())
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde du fichier temporaire {uploaded_file.name} : {str(e)}")
                    continue

                try:
                    # Charger le fichier MP3
                    audio = AudioSegment.from_mp3(temp_input_path)
                    duration = len(audio)
                    ten_minutes = 10 * 60 * 1000  # 10 minutes en millisecondes
                except Exception as e:
                    st.error(f"Erreur lors du chargement du fichier audio {uploaded_file.name} : {str(e)}")
                    continue

                all_transcriptions = []

                # Essayer de diviser et transcrire l'audio
                try:
                    for i in range(0, duration, ten_minutes):
                        chunk = audio[i : i + ten_minutes]
                        chunk_file_path = f"/tmp/{Path(uploaded_file.name).stem}_part_{i//ten_minutes}.mp3"
                        chunk.export(chunk_file_path, format="mp3")

                        # Ouvrir le segment du fichier audio
                        with open(chunk_file_path, "rb") as audio_file:
                            # Appeler l'API OpenAI pour transcrire le fichier audio
                            transcription = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_file,
                                prompt=whisper_prompt,
                            )

                        all_transcriptions.append(transcription.text)
                except Exception as e:
                    st.error(f"Erreur lors de la transcription du fichier {uploaded_file.name} : {str(e)}")
                    continue

                try:
                    # Combiner toutes les transcriptions et les sauvegarder dans un fichier texte
                    combined_transcription = "\n".join(all_transcriptions)
                    output_txt_path = f"/tmp/{Path(uploaded_file.name).stem}.txt"

                    with open(output_txt_path, "w") as text_file:
                        text_file.write(combined_transcription)
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde de la transcription pour {uploaded_file.name} : {str(e)}")
                    continue

                st.write(f"Traitement du fichier {uploaded_file.name} terminé")

                # Afficher la transcription dans le navigateur
                st.subheader(f"Transcription pour {uploaded_file.name}")
                st.text(combined_transcription)

                try:
                    # Fournir un lien de téléchargement pour le fichier texte
                    with open(output_txt_path, "r") as file:
                        st.download_button(
                            label="Télécharger les retranscriptions (TXT)",
                            data=file,
                            file_name=f"{Path(uploaded_file.name).stem}.txt",
                            mime="text/plain"
                        )
                except Exception as e:
                    st.error(f"Erreur lors de la création du lien de téléchargement pour {uploaded_file.name} : {str(e)}")

                # Mettre à jour la barre de progression
                st.progress((index + 1) / total_files)

            st.success("Tous les fichiers ont été traités avec succès")
        except Exception as e:
            st.error(f"Une erreur inattendue est survenue : {str(e)}")
    else:
        st.error("Veuillez téléverser au moins 1 fichier MP3")

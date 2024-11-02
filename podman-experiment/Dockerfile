
# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch and CUDA dependencies
RUN pip install torch==2.0.0 torchaudio==2.0.0

# Clone the WhisperX repository
RUN git clone https://github.com/m-bain/whisperX.git .

# Install WhisperX and its dependencies
RUN pip install -e .

# Set the default command to run when the container starts
CMD ["python", "-c", "import whisperx; print(whisperx.__version__)"]



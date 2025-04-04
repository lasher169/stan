FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    libopenblas-dev \
    liblapack-dev \
    libgflags-dev \
    swig \
    python3-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install numpy first for FAISS Python bindings
RUN pip3 install numpy

# Build FAISS with proper configuration
RUN git clone https://github.com/facebookresearch/faiss.git && \
    cd faiss && \
    cmake -B build \
        -DFAISS_ENABLE_PYTHON=ON \
        -DFAISS_ENABLE_GPU=OFF \
        -DBUILD_SHARED_LIBS=ON \
        -DCMAKE_BUILD_TYPE=Release \
        -DBLA_VENDOR=OpenBLAS \
        -DPython_EXECUTABLE=$(which python3) \
        -DBUILD_TESTING=OFF \ 
        -DFAISS_OPT_LEVEL=generic && \ 
    cmake --build build -j$(nproc --all) && \
    cd build && \
    make install && \
    ldconfig

# Install application Python dependencies
RUN pip install --no-cache-dir \
    schedule \
    faiss-cpu \
    duckdb \
    yfinance \
    pandas \
    ta \
    requests

# Copy application code
WORKDIR /app
COPY main.py /app

# Run application
CMD ["python", "main.py"]

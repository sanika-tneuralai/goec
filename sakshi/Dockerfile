FROM nvcr.io/nvidia/deepstream:6.4-triton-multiarch

WORKDIR /app

ENV PYTHONPATH="/opt/nvidia/deepstream/deepstream-6.4/lib:${PYTHONPATH}"
ENV LD_LIBRARY_PATH="/opt/nvidia/deepstream/deepstream-6.4/lib:${LD_LIBRARY_PATH}"

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python3", "main.py"]

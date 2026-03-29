# Usage:
#
# Build the image:
# docker build -t boxcast-exporter .
#
# Run the container (using environment variables):
# docker run --rm -it \
#   -e BOXCAST_CLIENT_ID=your_client_id \
#   -e BOXCAST_CLIENT_SECRET=your_client_secret \
#   -e BOXCAST_ACCOUNT_ID=your_account_id \
#   -v $(pwd)/broadcasts:/app/broadcasts \
#   boxcast-exporter
#
# Run the container (using a .env file):
# docker run --rm -it \
#   --env-file .env \
#   -v $(pwd)/broadcasts:/app/broadcasts \
#   boxcast-exporter
#

FROM public.ecr.aws/docker/library/python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application script
COPY boxcast_exporter.py .

# Set a volume so downloaded files can be easily mapped to the host
VOLUME ["/app/broadcasts"]

# Set the default output directory to match the volume
ENV BOXCAST_OUTPUT_DIR=/app/broadcasts

# Run the exporter script
ENTRYPOINT ["python", "boxcast_exporter.py"]

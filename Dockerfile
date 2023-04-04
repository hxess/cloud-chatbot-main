FROM python:3.8-slim-buster
WORKDIR /app
COPY projectchatbot.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 把这个替换成自己的telegram token
ENV ACCESS_TOKEN=""

ENV user="root"
ENV pwd="cptbtptp"
ENV sqlhost=51.120.244.80
ENV db="comp"

CMD ["python", "projectchatbot.py"]

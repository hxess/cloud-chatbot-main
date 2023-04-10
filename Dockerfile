FROM python:3.8-slim-buster
WORKDIR /app
COPY projectchatbot.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 把这个替换成自己的telegram token
ENV ACCESS_TOKEN="6178080288:AAH_avla6yFLcRFRse8G7zX28dOC0MX5Lew"

ENV user="root"
ENV pwd="cptbtptp"
ENV sqlhost=51.120.244.80
ENV db="comp"
ENV mongodb="mongodb://cloiud-computing:sVwNXL7xMF7R1RLC1zPXgECh2upmcPFuyt3J3KxnFpZYmDdKbbVmNGj4TjR1gQkuhDSVZdGeIVOHACDbXgylzA==@cloiud-computing.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@cloiud-computing@"

CMD ["python", "projectchatbot.py"]

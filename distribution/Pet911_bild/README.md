

sudo docker build -t build_v1.0 .
Если ошибка при сборке, то попробуйте прописать эту команду:
sudo docker build --no-cache -t build_v1.0 .

sudo docker run -it build_v1.0:latest
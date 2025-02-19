# Sử dụng image python làm base image
FROM python:3.9

# Đặt thư mục làm việc
WORKDIR /app

# Cài đặt các gói cần thiết cho locale
RUN apt-get update && apt-get install -y locales \
    && sed -i '/vi_VN.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen

# Thiết lập biến môi trường locale
ENV LANG vi_VN.UTF-8
ENV LANGUAGE vi_VN:vi
ENV LC_ALL vi_VN.UTF-8

# Copy các tệp requirements.txt vào container
COPY requirements.txt /app/

# Cài đặt các dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install mysqlclient
RUN pip install python-slugify

# Copy tất cả các tệp dự án vào container
COPY . /app/

# Thiết lập biến môi trường
ENV PYTHONUNBUFFERED 1

# Chạy lệnh migrate, import sản phẩm và collectstatic khi container khởi động
CMD ["sh", "-c", "python manage.py migrate && python manage.py import_products && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"]

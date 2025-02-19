import csv
from django.core.management.base import BaseCommand
from slugify import slugify
from shop.models import Product, Category

class Command(BaseCommand):
    help = 'Import products from a CSV file'

    def handle(self, *args, **kwargs):
        file_path = 'importer/products.csv'
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Xử lý danh mục chính
                parent_category, created = Category.objects.get_or_create(
                    title=row['category'],
                    defaults={'slug': self.get_unique_slug(row['category'], Category), 'is_sub': False}
                )

                # Xử lý danh mục phụ nếu có
                if row['sub_category']:
                    sub_category, created = Category.objects.get_or_create(
                        title=row['sub_category'],
                        sub_category=parent_category,  # Đảm bảo parent_category được truyền ở đây
                        defaults={'slug': self.get_unique_slug(row['sub_category'], Category), 'is_sub': True}
                    )
                    category = sub_category
                else:
                    category = parent_category

                # Chuyển đổi giá sang định dạng số
                price_str = row['price'].replace('.', '')
                price = float(price_str)

                # Tạo slug duy nhất cho sản phẩm
                product_slug = self.get_unique_slug(row['title'], Product)

                # Thêm sản phẩm vào CSDL
                product, created = Product.objects.get_or_create(
                    title=row['title'],
                    defaults={
                        'category': category,
                        'image_url': row['image_url'],
                        'description': row['description'],
                        'price': price,
                        'slug': product_slug
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Added product: {row["title"]}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Product already exists: {row["title"]}'))

    def get_unique_slug(self, base_slug, model_class):
        slug = slugify(base_slug)
        unique_slug = slug
        num = 1
        while model_class.objects.filter(slug=unique_slug).exists():
            unique_slug = f'{slug}-{num}'
            num += 1
        return unique_slug

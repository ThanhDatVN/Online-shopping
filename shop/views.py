from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from shop.models import Product, Category
from cart.forms import QuantityForm

import pickle
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import csr_matrix
import os
import random

# Xác định đường dẫn tuyệt đối đến thư mục ML_modeling
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML_MODELING_DIR = os.path.join(BASE_DIR, 'ML_modeling')

# Tải mô hình và dữ liệu đã lưu
with open(os.path.join(ML_MODELING_DIR, 'svd_model.pkl'), 'rb') as f:
    svd = pickle.load(f)

with open(os.path.join(ML_MODELING_DIR, 'tfidf_matrix.pkl'), 'rb') as f:
    tfidf_matrix = pickle.load(f)

with open(os.path.join(ML_MODELING_DIR, 'cosine_sim.pkl'), 'rb') as f:
    cosine_sim = pickle.load(f)

products_df = pd.read_pickle(os.path.join(ML_MODELING_DIR, 'products_df.pkl'))
ratings_df = pd.read_pickle(os.path.join(ML_MODELING_DIR, 'ratings_df.pkl'))

# Tạo ma trận thưa từ ratings_df
user_product_matrix = ratings_df.pivot(index='user_id', columns='product_id', values='rating').fillna(0)
user_product_sparse = csr_matrix(user_product_matrix)

# Kiểm tra kích thước của các ma trận
print("Kích thước user_product_sparse:", user_product_sparse.shape)
print("Kích thước svd.components_:", svd.components_.shape)

def get_content_based_recommendations(title, cosine_sim=cosine_sim):
    idx = products_df[products_df['title'] == title].index[0]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:11]
    product_indices = [i[0] for i in sim_scores]
    return products_df.iloc[product_indices][['title', 'price', 'image_url']]

def get_collaborative_recommendations(user_id, num_recommendations=5):
    user_idx = user_id - 1
    user_ratings = svd.transform(user_product_sparse)
    
    # Kiểm tra kích thước của user_ratings và svd.components_
    print("Kích thước user_ratings:", user_ratings.shape)
    
    if user_ratings.shape[1] != svd.components_.shape[0]:
        raise ValueError("Số lượng thành phần của user_ratings không khớp với số lượng thành phần của svd.components_.")
    
    # Đảm bảo user_vector là mảng 1 chiều
    user_vector = user_ratings[user_idx, :]
    if user_vector.ndim == 2:
        user_vector = user_vector.flatten()
    
    # In kích thước của user_vector và svd.components_ để kiểm tra
    print("Kích thước user_vector:", user_vector.shape)
    print("Kích thước svd.components_:", svd.components_.shape)
    
    # Thực hiện phép nhân ma trận
    try:
        scores = user_vector.dot(svd.components_)
    except ValueError as e:
        print("Lỗi khi thực hiện phép nhân ma trận:", e)
        raise
    
    top_product_indices = scores.argsort()[::-1][:num_recommendations]
    return products_df.iloc[top_product_indices][['title', 'price', 'image_url']]

def get_combined_recommendations(title, user_id, num_recommendations=5):
    content_recommendations = get_content_based_recommendations(title)
    collab_recommendations = get_collaborative_recommendations(user_id)
    combined_recommendations = pd.concat([content_recommendations, collab_recommendations]).drop_duplicates().head(num_recommendations)
    return combined_recommendations

def paginat(request, list_objects):
    p = Paginator(list_objects, 20)
    page_number = request.GET.get('page')
    try:
        page_obj = p.get_page(page_number)
    except PageNotAnInteger:
        page_obj = p.page(1)
    except EmptyPage:
        page_obj = p.page(p.num_pages)
    
    # Lưu trữ các tham số truy vấn khác trong URL (ví dụ: q)
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    page_obj.query_params = query_params
    
    return page_obj

def home_page(request):
    products = list(Product.objects.all())
    random.shuffle(products)  # Ngẫu nhiên danh sách sản phẩm
    context = {'products': paginat(request, products)}
    return render(request, 'home_page.html', context)

def product_detail(request, slug):
    form = QuantityForm()
    product = get_object_or_404(Product, slug=slug)
    recommendations = get_combined_recommendations(product.title, request.user.id)
    recommended_products = Product.objects.filter(title__in=recommendations['title'].tolist())
    
    context = {
        'title': product.title,
        'product': product,
        'form': form,
        'favorites': 'favorites',
        'recommended_products': recommended_products
    }
    if request.user.likes.filter(id=product.id).first():
        context['favorites'] = 'remove'
    return render(request, 'product_detail.html', context)

@login_required
def add_to_favorites(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    request.user.likes.add(product)
    return redirect('shop:product_detail', slug=product.slug)

@login_required
def remove_from_favorites(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    request.user.likes.remove(product)
    return redirect('shop:favorites')

@login_required
def favorites(request):
    products = request.user.likes.all()
    context = {'title': 'Favorites', 'products': products}
    return render(request, 'favorites.html', context)

def search(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(title__icontains=query).all()
    else:
        products = Product.objects.none()  # Trả về queryset rỗng nếu query là None
    context = {'products': paginat(request, products)}
    return render(request, 'home_page.html', context)

def filter_by_category(request, slug):
    """when user clicks on parent category
    we want to show all products in its sub-categories too"""
    result = []
    category = Category.objects.filter(slug=slug).first()
    if category:
        result.extend(Product.objects.filter(category=category.id).all())
        # check if category is parent then get all sub-categories
        if not category.is_sub:
            sub_categories = category.sub_categories.all()
            # get all sub-categories products 
            for sub_category in sub_categories:
                result.extend(Product.objects.filter(category=sub_category).all())
    context = {'products': paginat(request, result)}
    return render(request, 'home_page.html', context)

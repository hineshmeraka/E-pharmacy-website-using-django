from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Products, Cart, Order
import stripe
from django.conf import settings

# Set Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

# Home Page
def home(request):
    return render(request, "home.html")

# Search Functionality
def search(request):
    query = request.GET.get('search', '')
    if len(query) > 100:
        post = Products.objects.none()
    else:
        postName = Products.objects.filter(pname__icontains=query)
        postPrice = Products.objects.filter(price__icontains=query)
        post = postName.union(postPrice)

    if not post.exists():
        messages.warning(request, "No result found")

    return render(request, "search.html", {"post": post, "query": query})

# Products Page
def products(request):
    data = Products.objects.all()
    context = {"data": data}
    return render(request, "products.html", context)

# Cart Page
def cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    context = {"cart_items": cart_items, "total_price": total_price}
    return render(request, "cart.html", context)

# Add Product to Cart
def addcart(request, id):
    if request.user.is_authenticated:
        products = Products.objects.get(id=id)
        cart_item, created = Cart.objects.get_or_create(product=products, user=request.user)
        
        if not created:
            cart_item.quantity += 1
        
        cart_item.save()
        return redirect("/cart")
    else:
        messages.error(request, "You must be logged in to add products to the cart.")
        return redirect("/login")

# Delete Product from Cart
def delcart(request, id):
    try:
        cart_item = Cart.objects.get(id=id, user=request.user)
        cart_item.delete()
        messages.info(request, "Item removed from cart")
    except Cart.DoesNotExist:
        messages.warning(request, "Item not found in cart")
    return redirect('cart')

# Sign Up Functionality
def handlesignup(request):
    if request.method == "POST":
        uname = request.POST.get("username")
        email = request.POST.get("email")
        passw = request.POST.get("pass")
        cpassw = request.POST.get("cpass")
        
        if passw != cpassw:
            messages.warning(request, "Passwords do not match")
            return redirect("/signup")
        
        if User.objects.filter(email=email).exists():
            messages.warning(request, "This email is already registered")
            return redirect("/signup")
        
        User.objects.create_user(uname, email, passw)
        messages.info(request, "Sign-up successful. Please log in.")
        return redirect("/login")
    
    return render(request, "signup.html")

# Login Functionality
def handlelogin(request):
    if request.method == "POST":
        uname = request.POST.get("username")
        passw = request.POST.get("pass")
        try:
            myuser = authenticate(username=User.objects.get(email=uname), password=passw)
            if myuser is not None:
                login(request, myuser)
                messages.info(request, "Successfully logged in")
                return redirect("/")
            else:
                messages.error(request, "Login failed")
        except User.DoesNotExist:
            messages.error(request, "User does not exist")
    
    return render(request, "login.html")

# Logout Functionality
def handlelogout(request):
    logout(request)
    messages.info(request, "Successfully logged out")
    return redirect("/")

# Prescription Page
def prescription(request):
    return render(request, 'prescription.html')

# Handle Prescription Upload
def upload_prescription(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        notes = request.POST.get('notes')
        medicine_names = request.POST.getlist('medicine-name[]')
        
        matching_products = Products.objects.filter(pname__in=medicine_names)
        
        if matching_products.exists():
            return render(request, 'products.html', {'data': matching_products})
        else:
            messages.warning(request, "No matching products found.")
            return redirect('upload_prescription')

    return render(request, 'prescription.html')

# Checkout Page (Payment Page)
def checkout_view(request):
    try:
        cart_items = Cart.objects.filter(user=request.user)
        
        if not cart_items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('cart')

        total_price = sum(item.product.price * item.quantity for item in cart_items)

        # Create Stripe PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=int(total_price * 100),  
            currency='usd',
        )

        return render(request, 'payment_page.html', {'client_secret': intent.client_secret})

    except stripe.error.StripeError as e:
        messages.error(request, f"Payment error: {e.error.message}")
        return render(request, 'error_page.html', {'error': e.error.message})

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return render(request, 'error_page.html', {'error': str(e)})

# Handle Payment Confirmation
def payment_confirm(request):
    if request.method == 'POST':
        try:
            stripe_token = request.POST.get('stripeToken')
            client_secret = request.POST.get('client_secret')

            intent = stripe.PaymentIntent.confirm(
                client_secret,
                payment_method=stripe_token,
            )

            if intent.status == 'succeeded':
                Cart.objects.filter(user=request.user).delete()  # Clear cart after successful payment
                messages.success(request, "Payment successful!")
                return redirect('payment_success')
            else:
                return redirect('payment_failed')

        except stripe.error.StripeError as e:
            messages.error(request, f"Payment error: {e.user_message}")
            return redirect('payment_failed')

    return JsonResponse({'message': 'Invalid request'}, status=400)

# Payment Success
def payment_success(request):
    return render(request, 'payment_success.html')

# Payment Failed
def payment_failed(request):
    messages.error(request, "Payment failed. Please try again.")
    return render(request, 'payment_failed.html')


# Define payment_page to handle payment form rendering
def payment_page(request):
    try:
        # Get the user's cart or order details
        cart_items = Cart.objects.filter(user=request.user)
        total_amount = sum(item.product.price * item.quantity for item in cart_items)  # Calculate total amount

        if total_amount <= 0:
            messages.error(request, "Your cart is empty or there was an error in calculating the total amount.")
            return redirect('cart')

        # Create a PaymentIntent with Stripe
        intent = stripe.PaymentIntent.create(
            amount=int(total_amount * 100),  # Convert to cents
            currency='usd',
        )

        # Pass client_secret to the template to confirm the payment
        client_secret = intent.client_secret
        return render(request, 'payment_page.html', {'client_secret': client_secret})

    except stripe.error.StripeError as e:
        messages.error(request, f"An error occurred with Stripe: {str(e)}")
        return render(request, 'error_page.html', {'error': str(e)})

    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return render(request, 'error_page.html', {'error': str(e)})


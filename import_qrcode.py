import qrcode

def generate_activation_qr():
    """Generate a QR code that directs users to the bot with activation parameters."""
    # Activation URL
    activation_url = "https://t.me/YourBot?start=activate"  # Replace 'YourBot' with your bot's username

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,  # Controls the size of the QR Code
        box_size=10,  # Size of each box in pixels
        border=5  # Thickness of the border
    )
    qr.add_data(activation_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    img_filename = "bin_activation_qr.png"
    img.save(img_filename)
    print(f"QR code generated and saved as {img_filename}")

# Generate the QR code
generate_activation_qr()

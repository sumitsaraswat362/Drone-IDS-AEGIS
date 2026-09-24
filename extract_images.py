import fitz # PyMuPDF
import io
from PIL import Image

doc = fitz.open("Report Template - Grand challenge 3.pdf")
page = doc[0]
image_list = page.get_images(full=True)

for img_index, img in enumerate(image_list):
    xref = img[0]
    base_image = doc.extract_image(xref)
    image_bytes = base_image["image"]
    image_ext = base_image["ext"]
    
    # Save the image
    with open(f"extracted_img_{img_index}.{image_ext}", "wb") as f:
        f.write(image_bytes)
    print(f"Saved extracted_img_{img_index}.{image_ext}")

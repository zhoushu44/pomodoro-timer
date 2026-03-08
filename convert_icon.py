from PIL import Image

# 打开PNG图像
img = Image.open("番茄.png")

# 转换为ICO格式，包含多个尺寸
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_images = []

for size in sizes:
    try:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        ico_images.append(resized)
    except:
        pass

# 保存为ICO文件
ico_images[0].save("icon.ico", format="ICO", sizes=sizes)

print("✓ 图标转换成功！番茄.png -> icon.ico")
print(f"✓ 包含尺寸: {sizes}")

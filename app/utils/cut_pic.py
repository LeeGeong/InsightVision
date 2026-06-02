from PIL import Image

# 读取图片a和图片b
image_a = Image.open('a.jpg')  # 替换为图片a的路径
image_b = Image.open('b.jpg')  # 替换为图片b的路径

# 定义要从b中剪切的区域（左，上，右，下）
crop_area = (100, 100, 300, 300)  # 例如裁剪图片b从(100, 100)到(300, 300)

# 从b中裁剪区域
cropped_b = image_b.crop(crop_area)

# 选择图片a上粘贴的区域位置（左，上）
paste_position = (50, 50)  # 例如粘贴到a的(50, 50)位置

# 将裁剪后的b粘贴到a上
image_a.paste(cropped_b, paste_position)

# 保存修改后的图片a
image_a.save('modified_a.jpg')  # 你可以修改保存路径和文件名

print("操作完成，图片已保存为 'modified_a.jpg'")

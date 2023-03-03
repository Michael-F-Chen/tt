#!/usr/bin/env python

import inkex
import numpy as np
from scipy import interpolate
import lxml.etree


class BezierSurfaceTransform(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

        self.arg_parser.add_argument('-r', '--rows', action='store',
            dest='rows', default=3, help='Number of rows in the meshx')
        self.arg_parser.add_argument('-c', '--cols', action='store',
            dest='cols', default=3, help='Number of columns in the mesh')

    def effect(self):
        # 加载 lxml.etree 模块
        inkex.etree = lxml.etree

        # Get selected object (should be an image)
        # selected_object = self.selected[self.selected.keys()[0]]
        # selected_object = self.svg.selected[self.svg.selected.keys()[0]]
        selected_object = self.svg.selected[next(iter(self.svg.selected))]

        image_width = 0
        image_height = 0
        if selected_object.tag.endswith('use'):
            # 获取 use 元素的 clip-path 属性值
            clip_path_url = selected_object.get('clip-path')

            # 去除 url() 部分，得到路径的 ID
            clip_path_id = clip_path_url.replace('url(#', '').replace(')', '')

            # 在文档中查找路径元素
            path_element = self.xpath(f"//*[@id='{clip_path_id}']")[0]

            # 获取路径元素的长宽
            image_width = path_element.get('width')
            image_height = path_element.get('height')

        self.msg(selected_object)
        self.msg(dir(selected_object))

        # Get image data
        # image_data = selected_object.image.data

        # Get image dimensions
        # image_width = selected_object.image.width
        # image_height = selected_object.image.height
        image_width = selected_object.width
        image_height = selected_object.height

        # Get image position and scale
        x = selected_object.transformed_bbox().x
        y = selected_object.transformed_bbox().y
        scale_x = selected_object.transformed_bbox().width / image_width
        scale_y = selected_object.transformed_bbox().height / image_height

        # Create mesh
        rows = self.options.rows
        cols = self.options.cols
        step_x = image_width / cols
        step_y = image_height / rows
        mesh = []
        for j in range(rows):
            row = []
            for i in range(cols):
                row.append((i * step_x, j * step_y))
            mesh.append(row)
        mesh = np.array(mesh)

        # Get control points
        points = []
        for j in range(rows):
            for i in range(cols):
                points.append((mesh[j,i,0], mesh[j,i,1], selected_object.get('xlink:href')))
        points = np.array(points)

        # Interpolate control points
        tck, u = interpolate.splprep(points.T, s=0)
        u_new = np.linspace(0, 1, 10*image_width)
        points_new = interpolate.splev(u_new, tck)

        # Create Bezier surface
        control_points = []
        for j in range(rows):
            row = []
            for i in range(cols):
                row.append(points_new[j*cols+i])
            control_points.append(row)
        control_points = np.array(control_points)
        bezier_surface = interpolate.BSpline(*(control_points.T), kx=3, ky=3)

        # Apply Bezier surface transformation to image
        new_image_data = np.zeros_like(image_data)
        for j in range(image_height):
            for i in range(image_width):
                x_new, y_new = bezier_surface(i, j)
                x_new = int(x_new)
                y_new = int(y_new)
                if x_new < 0 or x_new >= image_width or y_new < 0 or y_new >= image_height:
                    continue
                new_image_data[j, i, :] = image_data[y_new, x_new, :]

        # 设置新图像的属性
        new_image_node = inkex.etree.Element('image')
        new_image_node.set('x', str(x))
        new_image_node.set('y', str(y))
        new_image_node.set('width', str(image_width))
        new_image_node.set('height', str(image_height))

        # 设置新图像的链接属性
        new_image_node.set('{http://www.w3.org/1999/xlink}href', source_file)

        # 创建新的滤镜
        new_filter = inkex.etree.Element('filter')
        new_filter.set('id', 'mesh-distort')

        # 创建新的feGaussianBlur节点
        blur_node = inkex.etree.Element('feGaussianBlur')
        blur_node.set('stdDeviation', '2')
        blur_node.set('result', 'blur')

        # 创建新的feColorMatrix节点
        color_matrix_node = inkex.etree.Element('feColorMatrix')
        color_matrix_node.set('in', 'blur')
        color_matrix_node.set('values', '0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 50 0')
        color_matrix_node.set('result', 'cm')

        # 创建新的feBlend节点
        blend_node = inkex.etree.Element('feBlend')
        blend_node.set('in', 'cm')
        blend_node.set('in2', 'SourceGraphic')
        blend_node.set('mode', 'multiply')
        blend_node.set('result', 'blend')

        # 将新节点添加到新滤镜中
        new_filter.append(blur_node)
        new_filter.append(color_matrix_node)
        new_filter.append(blend_node)

        # 将新滤镜添加到根元素中
        root.append(new_filter)

        # 创建新的feImage节点
        feImage = inkex.etree.Element('feImage')
        feImage.set('{http://www.w3.org/1999/xlink}href', source_file)
        feImage.set('width', str(image_width))
        feImage.set('height', str(image_height))
        feImage.set('preserveAspectRatio', 'none')
        feImage.set('transform', 'matrix(1 0 0 1 0 0)')
        feImage.set('x', str(x))
        feImage.set('y', str(y))
        feImage.set('filter', 'url(#mesh-distort)')

        # 将feImage节点添加到根元素中
        root.append(feImage)

        # 输出svg文件
        inkex.etree.ElementTree(root).write(output_file, encoding='UTF-8', xml_declaration=True)

if __name__ == "__main__":
    # print(__file__)
    effect = BezierSurfaceTransform()
    # effect.run()
    # This is the main entry point where execution should start
    # when run either as an Inkscape extension or within PyCharm.

    # If running in PyCharm we need to provide an svg file to work on.
    # To determine if we are running in PyCharm, we can look at __file__
    # If running in PyCharm, __file__ will be a full path, which will have a / separator.
    # If running in Inkscape, __file__ will just be the file name with no path and no /
    if '/' in __file__:
        # We are running in PyCharm
        input_file = r'D:\MyTestDrawing.svg'
        output_file = input_file
        effect.run([input_file, '--output=' + output_file])
    else:
        # We are running in Inkscape
        effect.run()

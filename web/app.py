from flask import Flask, render_template, send_from_directory, url_for, redirect, send_file, abort
import sqlite3
import os
from PIL import Image, ImageDraw, ImageFont
import io
import mimetypes
import magic
import fitz  # PyMuPDF для работы с PDF

app = Flask(__name__)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db.sqlite'))
MEDIA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'media'))

@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    news = conn.execute('SELECT id, title, external_id, media_uid FROM news ORDER BY added_at DESC').fetchall()
    conn.close()
    return render_template('index.html', news=news)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    item = conn.execute('SELECT * FROM news WHERE id=?', (news_id,)).fetchone()
    conn.close()
    media_url = None
    if item and item['media_uid']:
        media_url = url_for('media_file', filename=item['media_uid'])
    return render_template('detail.html', item=item, media_url=media_url)

@app.route('/media/<path:filename>')
def media_file(filename):
    file_path = os.path.join(MEDIA_DIR, filename)
    
    # Проверяем mime-type файла
    mime = magic.Magic(mime=True).from_file(file_path)
    
    # Для изображений и видео отдаем как есть
    if mime and (mime.startswith('image/') or mime.startswith('video/')):
        return send_from_directory(MEDIA_DIR, filename)
    
    # Для HTML и .bin файлов с HTML контентом
    if mime == 'text/html' or filename.endswith('.bin'):
        # Список кодировок для проверки
        encodings = ['utf-8', 'latin1', 'cp1251', 'iso-8859-1']
        html_markers = ['<!DOCTYPE html>', '<html', '<head>', '<body>', '<div', '<p>']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # Проверяем различные маркеры HTML контента
                    if any(marker in content.lower() for marker in html_markers):
                        return content, {'Content-Type': f'text/html; charset={encoding}'}
            except UnicodeDecodeError:
                continue  # Пробуем следующую кодировку
    
    # Для PDF файлов генерируем превью первой страницы
    if mime == 'application/pdf':
        try:
            pdf_document = fitz.open(file_path)
            if pdf_document.page_count > 0:
                page = pdf_document[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x масштаб для качества
                img_data = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                buf = io.BytesIO()
                img_data.save(buf, format='PNG')
                buf.seek(0)
                return send_file(buf, mimetype='image/png')
        except Exception as e:
            print(f"PDF conversion error: {e}")
    
    try:
        # Пробуем открыть как изображение
        with Image.open(file_path) as img:
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return send_file(buf, mimetype='image/png')
    except Exception:
        # Если ничего не подошло, генерируем превью с информацией о файле
        img = Image.new('RGB', (400, 200), color=(200, 200, 200))
        d = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        text = f'File: {filename}\nType: {mime}'
        d.multiline_text((10, 80), text, fill=(0, 0, 0), font=font, align='center')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')

@app.route('/back')
def go_back():
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

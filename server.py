from flask import Flask, render_template
import os

# Get the absolute path of the directory containing this file
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__,
            template_folder=os.path.join(basedir, 'web_ui'),
            static_folder=os.path.join(basedir, 'web_ui'),
            static_url_path='')

@app.route('/')
def index():
    return render_template('3d_test.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

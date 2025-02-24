FROM qgis/qgis:3.40

WORKDIR /code
RUN pip3 install virtualenv && virtualenv .venv --system-site-packages

COPY . .
RUN . .venv/bin/activate
RUN pip3 install -q -r requirements.txt --no-deps --only-binary=:all:
RUN pip3 install . --no-deps

ENV QT_QPA_PLATFORM=offscreen

CMD ["pytest"]

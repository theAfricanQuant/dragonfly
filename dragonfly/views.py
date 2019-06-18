# Copyright 2017-2019, The Johns Hopkins University Applied Physics Laboratory LLC
# All rights reserved.
# Distributed under the terms of the Apache 2.0 License.

from dragonfly import app, __version__
import flask
import io
import json
import random
import string
import os
from .data import OutputWriter, HintLoader, SentenceMarkerManager
from .mode import ModeManager
from .settings import SettingsManager
from .stats import Stats
from .translations import TranslationDictManager


@app.context_processor
def inject_dragonfly_context():
    version = __version__
    if app.debug:
        version += '.' + ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
    home_dir = app.config.get('dragonfly.home_dir')
    settings_manager = SettingsManager(home_dir)
    settings_manager.load()
    data = dict(version=version, sm=settings_manager)
    return data


@app.route('/', defaults={'filename': None})
@app.route('/<filename>')
def index(filename):
    mode = app.config.get('dragonfly.mode')
    manager = ModeManager(mode)
    file_index = flask.request.args.get('index')
    content = manager.render(app, filename, file_index)
    if not content:
        return flask.render_template('404.html', title="Error"), 404
    return content


@app.route('/save', methods=['POST'])
def save():
    data = flask.request.form['json']
    if not data:
        results = {'success': False, 'message': 'The server did not receive any data.'}
    else:
        writer = OutputWriter(app.config.get('dragonfly.output'))
        response = json.loads(data)
        writer.write(response)
        app.logger.info('Saving annotations for %s', response['filename'])
        results = {'success': True, 'message': 'Annotations saved.'}
    return flask.jsonify(results)


@app.route('/hints', methods=['GET'])
def hints():
    if app.config.get('dragonfly.hints'):
        hint_loader = HintLoader(app.config.get('dragonfly.hints'))
        hints = hint_loader.hints
    else:
        hints = []
    return flask.jsonify(hints)


@app.route('/marker', methods=['POST'])
def marker():
    manager = SentenceMarkerManager(app.config.get('dragonfly.data_dir'))
    document = flask.request.form['document']
    sentence = flask.request.form['sentence']
    manager.toggle(document, sentence)
    results = {'success': True, 'message': 'Marker saved.'}
    return flask.jsonify(results)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    home_dir = app.config.get('dragonfly.home_dir')
    settings_manager = SettingsManager(home_dir)
    if flask.request.method == 'GET':
        settings_manager.load()
        text_settings = {k: v for k, v in settings_manager.settings.items() if type(v) != bool}
        bool_settings = {k: v for k, v in settings_manager.settings.items() if type(v) == bool}
        return flask.render_template('modals/settings.html', text_settings=text_settings, bool_settings=bool_settings)
    else:
        new_settings = json.loads(flask.request.form['json'])
        settings_manager.save(new_settings)
        results = {'success': True, 'message': 'Settings saved.'}
        app.logger.info('Saved settings')
        return flask.jsonify(results)


@app.route('/translation', methods=['POST'])
def translation():
    home_dir = app.config.get('dragonfly.home_dir')
    data = flask.request.get_json('true')
    manager = TranslationDictManager(home_dir)
    manager.add(data['lang'], data['source'], data['translation'], data['type'])
    results = {'success': True, 'message': 'Translation saved.'}
    app.logger.info('Saved %s to the %s translation dictionary', data['source'], data['lang'])
    return flask.jsonify(results)


@app.route('/translation/delete', methods=['POST'])
def delete_translation():
    home_dir = app.config.get('dragonfly.home_dir')
    data = flask.request.get_json('true')
    manager = TranslationDictManager(home_dir)
    if manager.delete(data['lang'], data['source']):
        app.logger.info('Deleted %s from the %s translation dictionary', data['source'], data['lang'])
        results = {'success': True, 'message': 'Translation deleted.'}
    else:
        results = {'success':  False, 'message': 'Not in dictionary.'}
    return flask.jsonify(results)


@app.route('/translations/<lang>')
def translations(lang):
    home_dir = app.config.get('dragonfly.home_dir')
    manager = TranslationDictManager(home_dir)
    trans = manager.get(lang)
    return flask.jsonify(trans)


@app.route('/translations/export/<lang>')
def export_translations(lang):
    home_dir = app.config.get('dragonfly.home_dir')
    manager = TranslationDictManager(home_dir)
    filename = lang + '.json'
    file = manager.get_filename(lang)
    if not os.path.exists(file):
        file = io.BytesIO(b'{}')
    app.logger.info('Exported %s for %s', filename, lang)
    return flask.send_file(file, as_attachment=True, attachment_filename=filename, cache_timeout=0, add_etags=False)


@app.route('/translations/import/<lang>', methods=['POST'])
def import_translations(lang):
    home_dir = app.config.get('dragonfly.home_dir')
    manager = TranslationDictManager(home_dir)
    file = flask.request.files['dict']
    data = file.read().decode('utf-8')
    try:
        trans_dict = json.loads(data)
        num_new_items = manager.import_json(lang, trans_dict)
        results = {'success': True, 'message': '{} items added'.format(num_new_items)}
        app.logger.info('Imported %s for %s', file.filename, lang)
    except json.JSONDecodeError:
        results = {'success': False, 'message': 'Unrecognized format'}
    return flask.jsonify(results)


@app.route('/search', methods=['POST'])
def search():
    term = flask.request.form['term']
    results = app.dragonfly_index.lookup(term)
    app.logger.info('Returned %d results for %s', len(results['refs']), term)
    return flask.jsonify(results)


@app.route('/search/build', methods=['POST'])
def build_index():
    app.dragonfly_bg.build_index()
    results = {'success': True, 'message': 'Command queued'}
    return flask.jsonify(results)


@app.route('/stats')
def stats():
    output_dir = app.config.get('dragonfly.output')
    stats_data = Stats()
    stats_data.collect(output_dir)
    return flask.render_template('modals/stats.html', stats=stats_data)


@app.route('/tools')
def tools():
    lang = app.config.get('dragonfly.lang')
    return flask.render_template('modals/tools.html', lang=lang)

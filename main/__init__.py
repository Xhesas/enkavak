import argparse
import json
import secrets
from datetime import datetime as dt, timedelta as dttd
from random import shuffle

from flask import Flask, send_from_directory, send_file, request, redirect, render_template, make_response
from flask_uploads import UploadSet, configure_uploads # do 'pip install flask-reuploaded' instead of using the deprecated 'flask-uploads'
from jinja2 import TemplateNotFound
from werkzeug.middleware.proxy_fix import ProxyFix

LANG = {}
locs = ["reg", "registration", "ministries", "legislation", "jurisdiction", "magistrates", "senate", "bank", "military", "embassies", "elections", "doc", "documentation"]
output = None

app = Flask(__name__)
job_reg = UploadSet("jobReg")
app.config["UPLOADED_JOBREG_DEST"] = 'upload/ministry_job-reg'
app.config["SECRET_KEY"] = str(secrets.SystemRandom().getrandbits(128))
configure_uploads(app, job_reg)

@app.route('/resource/<resource>')
@app.route('/resources/<resource>')
def route_resources(resource):
    return send_from_directory('resources/', resource)

@app.route('/style')
@app.route('/style.css')
def route_style():
    return send_file('style/style.css')

@app.route('/form-style')
@app.route('/form-style.css')
@app.route('/formstyle')
@app.route('/formstyle.css')
def route_formstyle():
    return send_file('style/form.css')

@app.route('/favicon')
@app.route('/favicon.ico')
def route_favicon():
    return send_file('resources/banner.ico')

@app.route('/sitemap.xml')
def route_sitemap():
    return send_file('robots/sitemap.xml')

@app.route('/robots.txt')
def route_robots():
    return send_file('robots/robots.txt')

@app.route('/')
def route_index():
    return route_main("", "")

@app.route('/<lang>')
@app.route('/<lang>/')
def route_lang(lang):
    return route_main(lang, "")

@app.route('/<lang>/<path>')
def route_main(lang, path):
    if not lang in LANG['lang']:
        new_lang = [a for a in LANG["lang"] if a in [a.split(';')[0] for a in request.headers.get('Accept-Language').split(',')]] if request.headers.get('Accept-Language') else []
        return redirect('/' + (new_lang[0] if len(new_lang) > 0 else "en") + request.path, code=307)
    if path in ("", "index", "index.html"):
        return render_template('index.html', lang=lang, data=LANG['trans'], path=path)
    f = path.rsplit(".html", 1)[0] if path.endswith(".html") else path
    f = "reg" if f == "registration" else f
    if f in locs:
        return render_template(f + '.html', lang=lang, data=LANG['trans'], path=path)
    return make_response(not_found(None), 404)

@app.route('/<lang>/<location>/<path>')
def route_long(lang, location, path):
    if not lang in LANG['lang']:
        new_lang = [a for a in LANG["lang"] if a in [a.split(';')[0] for a in request.headers.get('Accept-Language').split(',')]] if request.headers.get('Accept-Language') else []
        return redirect('/' + (new_lang[0] if len(new_lang) > 0 else "en") + request.path, code=307)
    match next((i for i, v in enumerate(locs) if v == location), ""):
        case 0 | 1:
            try:
                return render_template('forms/' + path + ('' if path.endswith('.html') else '.html'), lang=lang, data=LANG['trans'], path='/'.join([location, path]))
            except TemplateNotFound:
                pass
        case 2:
            try:
                if path in ["reg", "purchase", "enroll"]:
                    pass
                return render_template('ministries/' + path + '.html', lang=lang, data=LANG['trans'], path='/'.join([location, path]))
            except TemplateNotFound:
                pass
        case 9:
            if path in ('reg', 'reg.html'):
                return render_template('forms/embassy.html', lang=lang, data=LANG['trans'], path='embassies/reg')
        case 10:
            match path:
                case "reg" | "reg.html":
                    return render_template('elections/reg.html', lang=lang, data=LANG['trans'], path='elections/reg')
                case "vote" | "vote.html":
                    date = validdate()
                    if date < dt.now() < date + dttd(days=3) or app.debug:
                        with open('templates/elections/candidates.json', 'r') as candidates_file:
                            candidates = json.load(candidates_file)
                        return render_template('elections/vote.html', lang=lang, data=LANG['trans'], path='elections/vote', candidates=candidates, lang_index=LANG['lang'].index(lang))
                    else:
                        return render_template('elections/none.html', lang=lang, data=LANG['trans'], path='elections/vote', date=do_date(lang, date))
        case 11 | 12:
            if path.rsplit(".html", 1)[0] if path.endswith(".html") else path == "laevnames":
                with open('templates/doc/names.json', 'r') as names_file:
                    names = json.load(names_file)
                o = {
                    'given': [],
                    'genus': [],
                    'relative': [],
                    'glottic': []
                }
                for name in sorted(names, key=lambda a: a['laev']):
                    o[name['type']].append({
                        'laev': name['laev'],
                        'translit': name['translit'],
                        'meaning': name['meaning']
                    })
                return render_template('doc/laevnames.html', lang=lang, data=LANG['trans'], path='doc/laevnames', names=o)
    return make_response(not_found(None), 404)

@app.route('/<lang>/ministries/<ministry>/<path>')
def route_ministry(lang, ministry, path):
    if not lang in LANG['lang']:
        new_lang = [a for a in LANG["lang"] if a in [a.split(';')[0] for a in request.headers.get('Accept-Language').split(',')]] if request.headers.get('Accept-Language') else []
        return redirect('/' + '/'.join([new_lang[0] if len(new_lang) > 0 else "en", 'ministries', ministry, path]), code=307)
    match '/'.join([ministry, path]):
        case "mbb/purchase" | "mbb/purchase.html":
            return render_template('ministries/purchase.html', lang=lang, data=LANG['trans'], path='ministries/mbb/purchase')
        case "mfb/enroll" | "mfb/enroll.html":
            return render_template('ministries/enroll.html', lang=lang, data=LANG['trans'], path='ministries/mfb/enroll')
    if path in ["reg", "reg.html", "register", "register.html"]:
        return render_template('ministries/reg.html', lang=lang, data=LANG['trans'], path='ministries/' + ministry + '/reg', ministry=ministry)
    return make_response(not_found(None), 404)

@app.route('/reg/citizen', methods=["POST"])
def register_citizen():
    save_message(
        request.form.get("name-mod"),
        {'name': "Citizenship-Form", 'values': request.form.to_dict(), 'book': generate_book("citizen-certificate", request.form.to_dict(), request.form.get("lang"))},
        request
    )
    return success()

@app.route('/reg/resident', methods=["POST"])
def register_resident():
    save_message(
        request.form.get("name-mod"),
        {'name': "Residentship-Form", 'values': request.form.to_dict(), 'book': generate_book("resident-certificate", request.form.to_dict(), request.form.get("lang"))},
        request
    )
    return success()

@app.route('/reg/visa', methods=["POST"])
def register_visa():
    save_message(
        request.form.get("name" if request.form.get("name-rom") == "" else "name-rom"),
        {'name': "Visa-Form", 'values': request.form.to_dict(), 'book': generate_book("visa", request.form.to_dict(), request.form.get("lang-pref"))},
        request
    )
    return success()

@app.route('/reg/company', methods=["POST"])
def register_company():
    save_message(
        request.form.get("name" if request.form.get("name-rom") == "" else "name-rom"),
        {'name': "Company-Form", 'values': request.form.to_dict(), 'book': generate_book("company-registration", request.form.to_dict(), request.form.get("lang"))},
        request
    )
    return success()

@app.route('/ministries/mbb/plot', methods=["POST"])
@app.route('/ministries/mbb/permit', methods=["POST"])
def buy_plot():
    issue = request.form.get("issue")
    vals = {
        "issue": issue,
        "name": request.form.get("name") if issue == "default" else request.form.get("country"),
        "signing": request.form.get("name") if issue == "default" else request.form.get("name-leader"),
        "id": request.form.get("id") if issue == "default" else "",
        "address": request.form.get("address")
    }
    save_message(
        vals['signing'],
        {'name': ("Plot" if request.path == '/ministries/mbb/plot' else "Buildingpermit") + "-Form", 'values': vals, 'book': generate_book("plot-purchase" if request.path == '/ministries/mbb/plot' else "building-permit", vals, 'en')},
        request
    )
    return success()

@app.route('/ministries/mfb/enroll-class', methods=["POST"])
@app.route('/ministries/mfb/enroll-exam', methods=["POST"])
def enroll():
    save_message(
        request.form.get("name"),
        {'name': ("Class" if request.path == '/ministries/mfb/enroll-class' else "Exam") + "-Application", 'values': request.form.to_dict()},
        request
    )
    return success()

@app.route('/embassies/reg', methods=["POST"])
@app.route('/elections/reg', methods=["POST"])
def register_embassy_or_election():
    save_message(
        request.form.get("name"),
        {'name': ("Embassy" if request.path == '/embassies/reg' else "Election") + "-Registration", 'values': request.form.to_dict()},
        request
    )
    return success()

@app.route('/elections/vote', methods=["POST"])
def vote():
    date = validdate()
    if not (date < dt.now() < date + dttd(days=3) or app.debug):
        return redirect('/elections/vote', code=302)
    with open('voting/voted.json', 'r') as voted_file:
        voted = json.load(voted_file)
    voter = {
        "id": request.form.get("id"),
        "num": request.form.get("num"),
        "user": {
            "address": request.environ.get('HTTP_X_REAL_IP', request.remote_addr),
            "client": request.headers["User-Agent"]
        },
        "time-UTC": str(dt.now())
    }
    vote_content = {
        "magistrate": request.form.getlist("magistrate"),
        "senator": request.form.getlist("senator")
    }
    if not ({"id": voter['id'], "num": voter['num']} in voted['valid']) or len([a for a in (voted[str(date)] if str(date) in voted else []) if a['id'] == voter['id']]) > 0:
        return make_response(render_template('elections/error.html'), 403)
    if str(date) not in voted:
        voted[str(date)] = []
    voted[str(date)].append(voter)
    with open('voting/voted.json', 'w') as voted_file:
        json.dump(voted, voted_file, indent=4, ensure_ascii=False)
    with open('voting/votes.json', 'r') as votes_file:
        filedata = json.load(votes_file)
    if str(date) not in filedata:
        filedata[str(date)] = []
    filedata[str(date)].append(vote_content)
    shuffle(filedata[str(date)])
    with open('voting/votes.json', 'w') as votes_file:
        json.dump(filedata, votes_file, indent=4, ensure_ascii=False)
    return render_template('elections/voted.html')

@app.route('/ministries/<ministry>/reg', methods=["POST"])
@app.route('/ministries/<ministry>/register', methods=["POST"])
def register_ministry(ministry):
    try:
        filepath = "upload/ministry_job-reg/" + request.files.get('file').filename
        job_reg.save(request.files.get('file'))
    except Exception as e:
        filepath = "Error saving file: " + str(e)
    save_message(
        request.form.get('name'),
        f"name: {request.form.get('name')}\nid: {request.form.get('id')}\nministry: {ministry}\nposition: {request.form.get('position')}\ndescription: {request.form.get('description')}",
        request,
        uploaded_file=filepath
    )
    return success()

def save_message(name, msg, r, uploaded_file=None):
    o = {
        "name": name,
        "message": msg,
        "file": uploaded_file if uploaded_file else "",
        "user": {
            "address": r.environ.get('HTTP_X_REAL_IP', r.remote_addr),
            "client": r.headers["User-Agent"]
        },
        "time-UTC": str(dt.now()),
        "page": r.headers["Host"] + r.path
    }
    if not output:
        print(o)
    else:
        with open(output, "r") as outputfile:
            filedata = json.load(outputfile)
        filedata['requests'].append(o)
        with open(output, "w") as outputfile:
            json.dump(filedata, outputfile, indent=4, ensure_ascii=False)

def generate_book(trans_id, vals, lang):
    try:
        return [a for a in LANG['trans-doc'] if a['id'] == trans_id][0][lang].format_map((vals | {"id_1": "{id}", "issue_date": str(do_date(lang, dt.now()))}))
    except Exception as e:
        print("failed getting the translated doc: " + str(e))
        return ""

@app.errorhandler(404)
def not_found(_):
    return render_template('not_found.html')

@app.errorhandler(400)
def bad_request(_):
    return render_template('/bad_request.html')

def success():
    return render_template('/successful_upload.html')

def validdate():
    return dt(2026, 7, 30) #actually calculate the next voting day. e.g. the first of the next laevanaak month at 00:00:00

def do_date(lang, date):
    match lang:
        case "de":
            return date.strftime("%d.%m.%Y")
        case "lv":
            return date.strftime("%x")
        case "lat":
            roman_months = {
                1: ("Jan.", "Kal.", "Non.", "Eid."),
                2: ("Feb.", "Kal.", "Non.", "Eid."),
                3: ("Mart.", "Kal.", "Non.", "Eid."),
                4: ("Apr.", "Kal.", "Non.", "Eid."),
                5: ("Mai.", "Kal.", "Non.", "Eid."),
                6: ("Iun.", "Kal.", "Non.", "Eid."),
                7: ("Iul.", "Kal.", "Non.", "Eid."),
                8: ("Aug.", "Kal.", "Non.", "Eid."),
                9: ("Sept.", "Kal.", "Non.", "Eid."),
                10: ("Oct.", "Kal.", "Non.", "Eid."),
                11: ("Nov.", "Kal.", "Non.", "Eid."),
                12: ("Dec.", "Kal.", "Non.", "Eid.")
            }

            kalends = 1
            nones = {3: 7, 5: 7, 7: 7, 10: 7}.get(date.month, 5)
            ides = {3: 15, 5: 15, 7: 15, 10: 15}.get(date.month, 13)

            month_name, kal, non, eid = roman_months[date.month]

            if date.day == kalends:
                return f"{kal} {month_name}"
            elif date.day == nones:
                return f"{non} {month_name}"
            elif date.day == ides:
                return f"{eid} {month_name}"
            elif date.day < nones:
                return f"a.d. {int_to_roman(nones - date.day + 1)} {non} {month_name}"
            elif date.day < ides:
                return f"a.d. {int_to_roman(ides - date.day + 1)} {eid} {month_name}"
            else:
                next_month = date.month + 1 if date.month < 12 else 1
                next_month_name, _, _, _ = roman_months[next_month]
                days_to_kalends = (dt(date.year, next_month, 1) - date).days
                return f"a.d. {int_to_roman(days_to_kalends)} Kal. {next_month_name}"
        case _:
            return date.strftime("%x")

def int_to_roman(n):
    roman_numerals = {
        1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
        6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
        11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV",
        16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX"
    }
    return roman_numerals.get(n, str(n))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--Output", type=str, help="Defines the output file for POST messages")
    parser.add_argument("-d", "--Debug", action="store_true", help="Activate debug mode")
    args = parser.parse_args()
    output = args.Output if args.Output else None
    with open('lang.json', 'r') as file:
        LANG = json.load(file)
    # check if voting/voted.json and voting/votes.json exist, if not create them
    try:
        with open('voting/voted.json', 'x') as file:
            json.dump({'valid':[]}, file, indent=4)
        with open('voting/votes.json', 'x') as file:
            json.dump({}, file, indent=4)
    except FileExistsError:
        pass
    # set proper wsgi for app if not debug
    if not args.Debug:
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )
    app.run(port=5003, debug=args.Debug)
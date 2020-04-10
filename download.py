from bs4 import BeautifulSoup
import pathlib
import requests
import webcolors
import json

data_url = 'https://en.wikipedia.org/wiki/National_colours'
country_name_url = 'https://raw.githubusercontent.com/stefangabos/world_countries/master/data/en/countries.json'
country_name_normalization_filepath = pathlib.Path('country-normalization.json')
country_isonames_filepath = pathlib.Path('country-iso3166.json')

output_dir = pathlib.Path('data')
hexcolor_output_file = output_dir / ('national-colors-hex.json')
rgbcolor_output_file = output_dir / ('national-colors-rgb.json')

organisation_key = 'Organisation'
country_key = 'Country'
colors_key = 'Primary'
secondary_colors_key = 'Secondary'

def parse_color(span):
    styles = span.attrs['style'].split(';')
    styles = [style.strip() for style in styles]
    # could parse contrasting color from color css attribute here
    for style in styles:
        if style.startswith('background-color:'):
            _, value = style.split(':')
            value = value.strip()
            try:
                value = webcolors.name_to_hex(value)
            except ValueError:
                value = webcolors.normalize_hex(value)
            return value
    raise ValueError('no color found for %s' % span)



def main():
    with country_name_normalization_filepath.open('r') as f:
        country_name_normalizations = json.load(f)

    with country_isonames_filepath.open('r') as f:
        country_isonames = json.load(f)

    resp = requests.get(country_name_url)
    resp.raise_for_status()
    country_names = json.loads(resp.text)
    country_names = dict([(c['name'], c['alpha2']) for c in country_names])


    resp = requests.get(data_url)
    resp.raise_for_status()
    dom = BeautifulSoup(resp.text)

    output_dir.mkdir(exist_ok=True)

    color_data = {}

    for table in dom.find_all('table', { 'class': 'wikitable' }):
        rows = table.find_all('tr')

        # find column indices
        headers = [cell.text.strip() for cell in rows[0].find_all('th')]
        # skip organisations
        if headers[0] == organisation_key:
            continue
        icol_country = headers.index(country_key)
        icol_colors = headers.index(colors_key)
        icol_colors_secondary = headers.index(secondary_colors_key)

        for i, row in enumerate(rows[1:]):
            cells = row.find_all('td')

            country_name = cells[icol_country].text.strip()

            primary_colors = [parse_color(span) for span in cells[icol_colors].find_all('span')]
            secondary_colors = [parse_color(span) for span in cells[icol_colors_secondary].find_all('span')]
            assert country_name not in color_data, 'duplicate country_name: ' + country_name

            country_name = country_name_normalizations.get(country_name, country_name)

            country_iso = country_names.get(country_name, None)
            if not country_iso:
                country_iso = country_isonames.get(country_name, None)
            if not country_iso:
                print('WARNING: missing iso code for ' + country_name + '. Skipping.')
                continue

            color_data[country_iso] = primary_colors

    with hexcolor_output_file.open('w') as f:
        json.dump(color_data, f)

    color_data_rgb = dict([(country, [webcolors.hex_to_rgb(c) for c in colors]) for country, colors in color_data.items()])
    with rgbcolor_output_file.open('w') as f:
        json.dump(color_data_rgb, f)



if __name__ == '__main__':
    main()

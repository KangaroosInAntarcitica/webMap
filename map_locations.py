import folium
import json
from geopy.geocoders import ArcGIS as geocoder


def read_locations(year, population_dict=None):
    """
    (str, dict) -> (dict)
    reads the 'locations.list' file and returns a dict of following format:
    {location (string name): [list of film names]}

    takes an optional argument population_dict, to which it writes information
    about the amount of films in a country
    """
    result = {}
    with open('locations.list', 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            # get the location
            line = line.split('\t')
            location = line[-2] if line[-1][0] == '(' else line[-1][:-1]

            line = line[0].split('(')
            # get rid of all ' because they cause errors in HTML code
            name = line[0].replace('\'', '"')
            if len(line) > 1 and line[1][0:4] == year:

                # update the population data with films number
                country = location.split(', ')[-1]
                if country == 'USA':
                    country = 'United States'
                elif country == 'UK':
                    country = 'United Kingdom'
                if population_dict and country in population_dict:
                    population_dict[country][1] += 1

                # add location data to the result dict
                if location not in result:
                    result[location] = [name]
                elif name not in result[location]:
                    result[location].append(name)

    return result


def parse_locations_from_file(films_dict, file_name):
    """
    (dict) -> (dict)

    takes a dict with film names as keys
    returns a dict with film coordinates as keys
    keys are of format: tuple(latitude, longitude)
    Takes all the information from a pre-created file
    """
    result = {}
    with open(file_name, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            line = line.split('\t')

            if line[0] in films_dict:
                # in file: name lng lat
                location = (float(line[2]), float(line[1]))
                if location not in result:
                    result[location] = films_dict[line[0]]
                else:
                    result[location] += films_dict[line[0]]

    return result


def parse_locations(films_dict):
    """
    (dict) -> (dict)

    takes a dict with film names as keys
    returns a dict with film coordinates as keys
    keys are of format: tuple(latitude, longitude)
    """
    result = {}
    geolocator = geocoder()

    for key, values in films_dict.items():
        try:
            location = geolocator.geocode(key, timeout=2)
            location = (location.latitude, location.longitude)
        except:
            # timeout or server error
            location = (None, None)

        # for testing and checking reasons print all the data
        print(values, location)
        # in some cases different location strings might point to the place
        # with the same coordinates
        if location not in result:
            result[location] = values
        else:
            result[location] += values

    return result


def write_html_list(values):
    """
    (list) -> (str)
    returns a list formated for use in an html file
    """
    result = '<div> <h4>Films: ' + str(len(values)) + '</h4>'
    result += '<div style="font-size: 14; width: 300px; max-height: 200px; \
    overflow-y: scroll; padding-left: 5px;"><ol style="padding-left: 15px;">'
    for item in values:
        result += '<li>' + item + '</li>'
    return result + '</ol> </div> </div>'


def open_population_data():
    """
    reads data from the 'world.json' file
    returns data, population_dict
    data - all the contents of the file
    population_dict - a dictionary, containing information about the population
    {name: [population, 0]} (0 is to fill in the films amount data)
    """
    population_dict = {}
    data = json.load(open('world.json', 'r', encoding='utf-8-sig',
                          errors='ignore'))

    # read the population data if item has properties
    for item in data['features']:
        if item['properties']:
            properties = item['properties']
            population_dict[properties['NAME']] = [properties['POP2005'], 0]

    return data, population_dict


def create_markers_group(locations_dict, name, func=lambda x: x):
    """
    Creates a marker group with the information given in films_dict
    (coordinates as keys)
    Takes an optional parameter func, which is applied to every value
    """
    group = folium.FeatureGroup(name=name)
    for location, values in locations_dict.items():
        if location[0] and location[1]:
            group.add_child(folium.Marker(location=[location[0], location[1]],
                                          popup=func(values),
                                          icon=folium.Icon()))
    return group


def create_choropleth(population_data, population_dict, index, name, color):
    """
    Creates a choropleth from the data given.
    population_data, population_dict - pre-created structures
    index - index of column in population dict
    (0 - population, 1 - films)
    name, color: specific properties for the choropleth
    """
    # find the maximal value in the selected coulumn
    maximal = max(population_dict.values(), key=lambda x:x[index])[index]

    def opacity(name, min_val=0.1, max_val=0.6):
        """ returns different opacity values depending on value / maximum """
        current = population_dict[name][index]
        val = current / maximal / max_val

        val = min_val if 0 < val < min_val else val
        return val if val < 0.5 else 0.5

    def style(feature):
        return {
            'fillColor': color,
            'color': '#000', 'weight': 1, 'dashArray': '5, 5',
            'fillOpacity': opacity(feature['properties']['NAME'])
        }

    return folium.GeoJson(population_data, name=name, style_function=style)


def show_on_map(locations_dict, population_data, population_dict, year):
    """
    Displays all the data on map

    Creates a map. Adds 3 layers to the map: films location, population data
    and film count
    """
    new_map = folium.Map(location=[0, 0], zoom_start=4)

    # create markers group and choropleth layers
    group = create_markers_group(locations_dict, 'Films', write_html_list)
    choropleth_pop = create_choropleth(population_data, population_dict,
                                       0, 'Population', '#F00')
    choropleth_films = create_choropleth(population_data, population_dict,
                                         1, 'Films count', '#0F4')

    # add all the stuff to new_map and save it
    new_map.add_child(choropleth_pop)
    new_map.add_child(choropleth_films)
    new_map.add_child(group)
    new_map.add_child(folium.LayerControl())
    new_map.save('​Films_map_' + year + '.html')


def main():
    year = input('Enter year (number): ')
    geocode_file = \
        input('Enter file name with geocode info (geocodes.list or nothing): ')
    population_data, population_dict = open_population_data()

    # find films locations, geocode them and info the user about numbers
    films_dict = read_locations(year, population_dict)
    if geocode_file:
        locations_dict = parse_locations_from_file(films_dict, geocode_file)
    else:
        locations_dict = parse_locations(films_dict)

    print('Unique names: ', len(films_dict),', coords: ', len(locations_dict))

    # display on map
    show_on_map(locations_dict, population_data, population_dict, year)


if __name__ == '__main__':
    main()
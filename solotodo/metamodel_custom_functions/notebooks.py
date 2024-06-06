from decimal import Decimal

from solotodo.metamodel_custom_functions.utils import pretty_dimensions


def ordering_value(im):
    m = im.model.name
    if m == "NotebookScreen":
        return im.size.size * 10 + (
            im.resolution.horizontal * im.resolution.vertical
        ) / Decimal(1000000)

    if m == "NotebookScreenResolution":
        return im.horizontal * im.vertical


def pretty_battery(elastic_dict):
    """
    Returns a prettified version of the battery data or a default message
    if no info is available
    """
    additions = []
    if elastic_dict["battery_mah"] > 0:
        additions.append("{} mAh".format(elastic_dict["battery_mah"]))
    if elastic_dict["battery_mv"] > 0:
        additions.append("{} mV".format(elastic_dict["battery_mv"]))
    if elastic_dict["battery_mwh"] > 0:
        additions.append("{} mWh".format(elastic_dict["battery_mwh"]))
    result = " | ".join(additions)

    if "battery_cells" in elastic_dict and elastic_dict["battery_cells"] > 0:
        if result:
            result = "(" + result + ")"

        result = "{} celdas {}".format(elastic_dict["battery_cells"], result)

    if not result:
        result = "No hay información disponible"

    return result


def get_score_general(elastic_dict):
    """
    Calculates and returns the score of this notebook when running normal
    applications on a fictional scale from 0 to 1000, but that can
    overflow over 1000. Consider 1000 to be a reasonable maximum.
    """

    # Heuristical calculation based on the current scores in the DB
    processor_rating = min(elastic_dict["processor_speed_score"] / 28000.0, 1.0)
    ram_rating = min(float(elastic_dict["ram_quantity_value"]) / 16.0, 1.0)
    return int(800 * processor_rating + 200 * ram_rating)


def get_score_games(elastic_dict):
    """
    Calculates and returns the score of this notebook when running 3D
    games on a fictional scale from 0 to 1000, but that can
    overflow over 1000. Consider 1000 to be a reasonable maximum.
    """

    # Heuristical calculation based on the current scores in the DB
    processor_rating = min(elastic_dict["processor_speed_score"] / 28000.0, 1.0)
    ram_rating = min(float(elastic_dict["ram_quantity_value"]) / 16.0, 1.0)
    gpu = elastic_dict.get("processor_gpu_speed_score", 0)

    if "dedicated_video_card_id" in elastic_dict:
        dedicated = elastic_dict["dedicated_video_card_speed_score"]
    else:
        dedicated = 0

    video_card_score = max(gpu, dedicated)

    # Heuristical calculation based on the current scores in the DB
    video_card_rating = min(video_card_score / 35000.0, 1.0)

    return int(100 * processor_rating + 50 * ram_rating + 850 * video_card_rating)


def get_score_mobility(elastic_dict):
    """
    Calculates and returns the score of this notebook regarding its
    mobility (size, weight, etc) on a fictional scale from 0 to 1000,
    but that can overflow over 1000. Consider 1000 to be a reasonable
    maximum.
    """

    # Heuristical calculations based on the current scores in the DB
    screen_rating = min(
        max(2.25 - 0.125 * float(elastic_dict["screen_size_size"]), 0), 1.0
    )
    weight_rating = min(max((3000 - elastic_dict["weight"]) / 2000.0, 0), 1.0)
    processor_rating = min(
        max((4 - elastic_dict["processor_consumption"]) / 3.0, 0), 1.0
    )

    return int(400 * screen_rating + 300 * weight_rating + 300 * processor_rating)


def get_sugestions_parameters(elastic_search_result):
    searching_criteria = {}

    if elastic_search_result["score_games"] >= 450:
        searching_criteria["ordering"] = "-score_games"
    elif elastic_search_result["score_mobility"] >= 700:
        searching_criteria["ordering"] = "-score_mobility"
        searching_criteria["max_screen_size"] = elastic_search_result[
            "screen_size_family_id"
        ]
        searching_criteria["min_screen_size"] = elastic_search_result[
            "screen_size_family_id"
        ]
    else:
        searching_criteria["ordering"] = "-score_general"

    return searching_criteria


def additional_es_fields(elastic_search_result, model_name):
    if model_name == "Notebook":
        result = {}

        result["gpus"] = []

        if "processor_gpu_id" in elastic_search_result:
            processor_gpu_dict = {}

            for key, value in elastic_search_result.items():
                if key.startswith("processor_gpu_"):
                    processor_gpu_dict[key.replace("processor_gpu_", "")] = value

            result["gpus"].append(processor_gpu_dict)

        if "dedicated_video_card_id" in elastic_search_result:
            dedicated_video_card_dict = {}

            for key, value in elastic_search_result.items():
                if key.startswith("dedicated_video_card_"):
                    dedicated_video_card_dict[
                        key.replace("dedicated_video_card_", "")
                    ] = value

            result["gpus"].append(dedicated_video_card_dict)

            pretty_dedicated_video_card = elastic_search_result[
                "dedicated_video_card_unicode"
            ]
        else:
            pretty_dedicated_video_card = "No posee"

        if result["gpus"]:
            main_gpu = result["gpus"][-1]
        else:
            main_gpu = None

        result["main_gpu"] = main_gpu
        result["pretty_battery"] = pretty_battery(elastic_search_result)
        result["pretty_ram"] = "{} {} ({})".format(
            elastic_search_result["ram_quantity_unicode"],
            elastic_search_result["ram_type_unicode"],
            elastic_search_result["ram_frequency_unicode"],
        )
        result["pretty_dimensions"] = pretty_dimensions(
            elastic_search_result, ["width", "height", "thickness"]
        )
        result["model_name"] = "{} {}".format(
            elastic_search_result["family_line_name"],
            elastic_search_result["name"],
        ).strip()
        result["pretty_dedicated_video_card"] = pretty_dedicated_video_card
        result["score_general"] = get_score_general(elastic_search_result)
        result["score_games"] = get_score_games(elastic_search_result)
        result["score_mobility"] = get_score_mobility(elastic_search_result)

        elastic_search_result["score_games"] = result["score_games"]
        elastic_search_result["score_mobility"] = result["score_mobility"]
        result["suggested_alternatives_parameters"] = get_sugestions_parameters(
            elastic_search_result
        )

        largest_storage_drive = sorted(
            elastic_search_result["storage_drive"],
            key=lambda x: x["capacity_value"],
            reverse=True,
        )[0]

        result["largest_storage_drive"] = largest_storage_drive

        result["processor_has_turbo_frequencies"] = (
            elastic_search_result["processor_frequency_value"]
            != elastic_search_result["processor_turbo_frequency_value"]
        )

        tags = []
        if result["score_games"] >= 300:
            tags.append("Gamer")

        if (
            elastic_search_result["screen_is_rotating"]
            and elastic_search_result["screen_is_touchscreen"]
        ):
            tags.append("Convertible")

        result["tags"] = tags

        warnings = []
        if elastic_search_result["keyboard_layout_unicode"] == "Desconocido":
            warnings.append(
                "No sabemos el idioma del teclado de este notebook, por "
                "favor confirma con la tienda antes de comprarlo"
            )
        elif elastic_search_result["keyboard_layout_unicode"] != "Español":
            warnings.append(
                "Este notebook no tiene teclado en español, por lo que hacer la "
                '"ñ", tildes, o símbolos especiales con él puede ser incómodo'
            )

        for storage_drive in elastic_search_result["storage_drive"]:
            if storage_drive["drive_type_unicode"] in ["SSD", "eMMC"]:
                break
        else:
            warnings.append(
                "Este notebook usa un disco duro (HDD) como unidad de "
                "almacenamiento, lo que lo vuelve lento para su uso normal. "
                "Recomendamos buscar equipos con almacenamiento SSD"
            )

        os_brand = elastic_search_result["operating_system_family_brand_unicode"]
        if os_brand == "Linux":
            warnings.append(
                "Este notebook usa Linux como sistema operativo, que es "
                "bastante diferente a Windows (lo más común en "
                "notebooks)"
            )
        elif os_brand == "FreeDOS":
            warnings.append(
                "Este notebook no incluye sistema operativo. "
                "Necesitará instalarle Windows u otro sistema operativo "
                "por su cuenta"
            )
        elif os_brand == "Google":
            warnings.append(
                "Este notebook usa Chrome OS como sistema operativo, que es "
                "un poco más limitado y no incluye las aplicaciones "
                "típicas disponibles en Windows (como Office)"
            )

        result["warnings"] = warnings

        return result

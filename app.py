{
    "version": "0.1",
    "title": "FaceFoodChef - Netflix Style Home",
    "type": "page",
    "content": [
        {
            "id": "hero_section",
            "elType": "section",
            "settings": {
                "_element_id": "hero_section",
                "content_width": "full",
                "min_height": 600,
                "background_background": "classic",
                "background_color": "#1A1A1A"
            },
            "elements": [
                {
                    "id": "hero_column",
                    "elType": "column",
                    "settings": {
                        "content_position": "middle"
                    },
                    "elements": [
                        {
                            "id": "main_heading",
                            "elType": "widget",
                            "widgetType": "heading",
                            "settings": {
                                "title": "FACEFOODCHEF: RECETAS, DIVERSIÓN Y COMUNIDAD.",
                                "align": "center",
                                "header_size": "h1",
                                "typography_typography": "custom",
                                "typography_font_size": 52,
                                "typography_font_weight": "600",
                                "text_color": "#E50914"
                            }
                        },
                        {
                            "id": "sub_heading",
                            "elType": "widget",
                            "widgetType": "heading",
                            "settings": {
                                "title": "¡Tu cocina en un clic! Descubre sabores y empieza a cocinar hoy mismo.",
                                "align": "center",
                                "header_size": "h4",
                                "text_color": "#FFFFFF",
                                "margin": {"top": "15", "right": "0", "bottom": "40", "left": "0", "unit": "px"}
                            }
                        },
                        {
                            "id": "hero_button",
                            "elType": "widget",
                            "widgetType": "button",
                            "settings": {
                                "text": "¡Ver Recetas Populares Ahora!",
                                "align": "center",
                                "button_type": "flat",
                                "background_color": "#E50914",
                                "text_color": "#FFFFFF",
                                "border_radius": {"unit": "px", "top": "5", "right": "5", "bottom": "5", "left": "5"}
                            }
                        }
                    ]
                }
            ]
        },
        {
            "id": "row_1_posts",
            "elType": "section",
            "settings": {
                "_element_id": "row_1_posts",
                "background_color": "#1A1A1A",
                "padding": {"top": "40", "right": "0", "bottom": "40", "left": "0", "unit": "px"}
            },
            "elements": [
                {
                    "id": "title_row_1",
                    "elType": "column",
                    "settings": {},
                    "elements": [
                        {
                            "id": "heading_row_1",
                            "elType": "widget",
                            "widgetType": "heading",
                            "settings": {
                                "title": "▶️ POSTRES RÁPIDOS Y FÁCILES",
                                "align": "left",
                                "header_size": "h3",
                                "text_color": "#FFFFFF"
                            }
                        },
                        {
                            "id": "posts_row_1",
                            "elType": "widget",
                            "widgetType": "posts",
                            "settings": {
                                "posts_per_page": 4,
                                "columns": 4,
                                "post_type": "post",
                                "show_image": "yes",
                                "show_title": "yes",
                                "show_meta": "",
                                "show_excerpt": "",
                                "meta_separator": " - ",
                                "text_color": "#FFFFFF"
                                // **NOTA:** DEBES FILTRAR AQUÍ POR CATEGORÍA
                            }
                        }
                    ]
                }
            ]
        }
    ]
}

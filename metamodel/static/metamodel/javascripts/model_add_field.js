$(function() {
    'use strict';

    function update_default_field() {
        $.getJSON('', {
            model: $('#id_model').val(),
            nullable: $('#id_nullable').is(':checked'),
            multiple: $('#id_multiple').is(':checked')
        }, function(response) {
            var default_widget_cell = $('#id_default').parent();

            var default_field_row = default_widget_cell.parent();
            if (response[0]) {
                default_field_row.show();
            } else {
                default_field_row.hide();
            }

            default_widget_cell.empty();

            var choices = response[1];

            var widget;

            if (choices == null) {
                widget = $('<input type="hidden" name="default" id="id_default" />');
            }  else if(typeof(choices) == 'string') {
                widget = $('<input type="' + choices + '" name="default" id="id_default" step="0.01" />');
            } else {
                widget = $('<select name="default" id="id_default"></select>');

                $.each(choices, function(idx, entry) {
                    widget.append($('<option value="' + entry[0] + '">' + entry[1] + '</option>'));
                });
            }

            default_widget_cell.append(widget);
        })
    }

    update_default_field();

    $('#id_model, #id_nullable, #id_multiple').change(function() {
        update_default_field()
    });
});
$(function() {
    'use strict';

    $('.add_new_link').on('click', function() {
        var url = $(this).attr('href');

        window.open(url, '_blank', 'width=700,height=700');
        return false;
    });
});

function popup_callback(model_instance) {
    console.log(model_instance);
    var matching_links = $('a[data-model="' + model_instance.model + '"');

    $.each(matching_links, function(idx, link) {
        var container = $(link).parent().find('select');

        container.append('<option value="' + model_instance.id + '">' + model_instance.name + '</option>');

        if (container.attr('multiple') == 'multiple') {
            container.find('option[value="' + model_instance.id  + '"]').prop('selected', true)
        } else {
            container.val(model_instance.id);
        }
    });
}
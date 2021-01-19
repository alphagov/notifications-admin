(function(global) {

  "use strict";

  var Modules = global.GOVUK.Modules;
  var Hogan = global.Hogan;

  let states = {
    'initial': Hogan.compile(`
      {{#showNowAsDefault}}
        <div class="radio-select__column">
          <div class="multiple-choice js-multiple-choice">
            <input checked="checked" id="{{name}}-0" name="{{name}}" type="radio" value="">
            <label class="block-label js-block-label" for="{{name}}-0">Now</label>
          </div>
        </div>
      {{/showNowAsDefault}}
      <div class="radio-select__column">
        {{#categories}}
          <input type='button' class='govuk-button govuk-button--secondary radio-select__button--category' aria-expanded="false" value='{{.}}' />
        {{/categories}}
      </div>
    `),
    'choose': Hogan.compile(`
      {{#showNowAsDefault}}
        <div class="radio-select__column">
          <div class="multiple-choice js-multiple-choice js-initial-option">
            <input checked="checked" id="{{name}}-0" name="{{name}}" type="radio" value="">
            <label for="{{name}}-0">Now</label>
          </div>
        </div>
      {{/showNowAsDefault}}
      <div class="radio-select__column">
        {{#choices}}
          <div class="multiple-choice js-multiple-choice js-option">
            <input type="radio" value="{{value}}" id="{{id}}" name="{{name}}" />
            <label for="{{id}}">{{label}}</label>
          </div>
        {{/choices}}
        <input type='button' class='govuk-button govuk-button--secondary radio-select__button--done' aria-expanded='true' value='Done' />
      </div>
    `),
    'chosen': Hogan.compile(`
      {{#showNowAsDefault}}
        <div class="radio-select__column">
          <div class="multiple-choice js-multiple-choice js-initial-option">
            <input id="{{name}}-0" name="{{name}}" type="radio" value="">
            <label for="{{name}}-0">Now</label>
          </div>
        </div>
      {{/showNowAsDefault}}
      <div class="radio-select__column">
        {{#choices}}
          <div class="multiple-choice js-multiple-choice">
            <input checked="checked" type="radio" value="{{value}}" id="{{id}}" name="{{name}}" />
            <label for="{{id}}">{{label}}</label>
          </div>
        {{/choices}}
      </div>
      <div class="radio-select__column">
        <input type='button' class='govuk-button govuk-button--secondary radio-select__button--reset' aria-expanded='false' value='Choose a different time' />
      </div>
    `)
  };

  let focusSelected = function(component) {
    $('[type=radio]:checked', component).focus();
  };

  Modules.RadioSelect = function() {

    this.start = function(component) {

      let $component = $(component);
      let render = (state, data) => {
        $component.html(states[state].render(data));
      };
      let choices = $('label', $component).toArray().map(function(element) {
        let $element = $(element);
        return {
          'id': $element.attr('for'),
          'label': $.trim($element.text()),
          'value': $element.prev('input').attr('value')
        };
      });
      let categories = $component.data('categories').split(',');
      let name = $component.find('input').eq(0).attr('name');
      let mousedownOption = null;
      let showNowAsDefault = (
        $component.data('show-now-as-default').toString() === 'true' ?
        {'name': name} : false
      );
      const reset = () => {
        render('initial', {
          'categories': categories,
          'name': name,
          'showNowAsDefault': showNowAsDefault
        });
      };
      const selectOption = (value) => {
        render('chosen', {
          'choices': choices.filter(
            element => element.value == value
          ),
          'name': name,
          'showNowAsDefault': showNowAsDefault
        });
        focusSelected(component);
      };
      const trackMouseup = (event) => {
        const parentNode = event.target.parentNode;

        if (parentNode === mousedownOption) {
          const value = $('input', parentNode).attr('value');

          selectOption(value);

          // clear tracking
          mousedownOption = null;
          $(document).off('mouseup', trackMouseup);
        }
      };

      $component
        .on('click', '.radio-select__button--category', function(event) {

          event.preventDefault();
          let wordsInDay = $(this).attr('value').split(' ');
          let day = wordsInDay[wordsInDay.length - 1].toLowerCase();
          render('choose', {
            'choices': choices.filter(
              element => element.label.toLowerCase().indexOf(day) > -1
            ),
            'name': name,
            'showNowAsDefault': showNowAsDefault
          });
          focusSelected(component);

        })
        .on('mousedown', '.js-option', function(event) {
          mousedownOption = this;

          // mouseup on the same option completes the click action
          $(document).on('mouseup', trackMouseup);
        })
        // space and enter, clicked on a radio confirm that option was selected
        .on('keydown', 'input[type=radio]', function(event) {

          // allow keypresses which aren’t enter or space through
          if (event.which !== 13 && event.which !== 32) {
            return true;
          }

          event.preventDefault();
          let value = $(this).attr('value');
          selectOption(value);

        })
        .on('click', '.radio-select__button--done', function(event) {

          event.preventDefault();
          let $selection = $('input[type=radio]:checked', this.parentNode);
          if ($selection.length) {

            render('chosen', {
              'choices': choices.filter(
                element => element.value == $selection.eq(0).attr('value')
              ),
              'name': name,
              'showNowAsDefault': showNowAsDefault
            });

          } else {

            reset();

          }
          focusSelected(component);

        })
        .on('click', '.radio-select__button--reset', function(event) {

          event.preventDefault();
          reset();
          focusSelected(component);

        });

      render('initial', {
        'categories': categories,
        'name': name,
        'showNowAsDefault': showNowAsDefault
      });

      $component.css({'height': 'auto'});

    };

  };

})(window);

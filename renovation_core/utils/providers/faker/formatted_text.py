from faker.providers import BaseProvider

localized = True

# 'Latin' is the default locale
default_locale = 'la'


class FormattedText(BaseProvider):
  def html(self):
    print(self.word_list)

  def markdown(self):
    pass

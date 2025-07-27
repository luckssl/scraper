class Site:
    def __init__(self, nome, url, seletor_produto, seletor_nome, seletor_preco):
        self.nome = nome            # Ex: "Mercado Livre"
        self.url = url              # Ex: "https://www.mercadolivre.com.br/"
        self.seletor_produto = seletor_produto    # Ex: (By.CLASS_NAME, "ui-search-layout__item")
        self.seletor_nome = seletor_nome          # Ex: (By.CLASS_NAME, "poly-component__title-wrapper")
        self.seletor_preco = seletor_preco        # Ex: (By.XPATH, '//span[@role="img" and @aria-roledescription="Valor"]')

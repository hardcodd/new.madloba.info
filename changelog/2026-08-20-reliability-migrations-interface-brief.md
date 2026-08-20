[← Предыдущая задача](2026-08-17-postgresql-test-isolation-brief.md) · [Все отчёты](README.md) · [Подробная версия](2026-08-20-reliability-migrations-interface-detailed.md)

# Обновил надёжность отзывов и страницы сайта

- **Дата:** 20 августа 2026 года
- **Коммиты:** [`45e094b`](https://github.com/hardcodd/new.madloba.info/commit/45e094b9f231acd88f2a0458d29a70157d5851e8), [`58e0581`](https://github.com/hardcodd/new.madloba.info/commit/58e0581808fcf3e2fef11a7cd3e6f35e3494e25d), [`1acb577`](https://github.com/hardcodd/new.madloba.info/commit/1acb577440e961b908728e13551a8bebf4bdfb01), [`0f03391`](https://github.com/hardcodd/new.madloba.info/commit/0f033911177d7445b31819ac8b0c4b380b4213a8), [`7f27d8b`](https://github.com/hardcodd/new.madloba.info/commit/7f27d8b95c11406dfd524b7d46c9291aff66a99b), [`d336212`](https://github.com/hardcodd/new.madloba.info/commit/d3362123ac77fdbd21b87ecd9e93873758d8d21a), [`6fd791e`](https://github.com/hardcodd/new.madloba.info/commit/6fd791e9301ae58da022f728a469f1e87a19d23d), [`b057971`](https://github.com/hardcodd/new.madloba.info/commit/b05797178f6223eaeeeb849bae8a0f4188892e21), [`ea8b1be`](https://github.com/hardcodd/new.madloba.info/commit/ea8b1bed868d9c4ad97908cd7ae0072df8ca8fb0)

Исправил обработку оценок в отзывах: сайт принимает только значения от 1 до 5 и использует в данных для поисковых систем только опубликованные корректные отзывы. Добавил недостающие обновления базы данных, чтобы изменения моделей безопасно переносились на сервер.

Также исправил перелистывание авторов, добавил русские подписи, улучшил списки на текстовых страницах и задал правильные пропорции изображений. Служебные описания кода сделал точнее.

Проверил весь набор изменений: все 35 автоматических тестов прошли, Django и Ruff не нашли ошибок, несохранённых изменений моделей нет. Пропорции изображений дополнительно проверены в браузере.

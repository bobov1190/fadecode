"""Контент пака «Алгоритмы для LeetCode», часть 1: бинарный поиск. Модуль подключается из build_algo.py."""

LESSONS_BS = [
    {
        "id": "bs_template",
        "title": "Бинарный поиск: шаблоны",
        "tag": "бинарный поиск · шаблон · LeetCode 704",
        "desc": "Классический поиск, lower_bound и upper_bound.",
        "task": "\n".join([
            "Реализуй три основных шаблона бинарного поиска по отсортированному массиву: классический поиск индекса (LeetCode 704), lower_bound и upper_bound. Эти заготовки пригодятся почти в каждой задаче на бинарный поиск.",
            "Пример: nums = [-1, 0, 3, 5, 9, 12], target = 9 → search вернёт 4.",
            "Пример: nums = [1, 2, 2, 2, 3], target = 2 → lower_bound вернёт 1, upper_bound вернёт 4.",
            "Сложность: O(log n) по времени, O(1) по памяти.",
        ]),
        "imports": "from typing import List",
        "cls": "class BinarySearch:",
        "blocks": [
            {
                "id": "search",
                "name": "search",
                "note": "Классика: ищет индекс target на закрытом отрезке [left, right] или возвращает -1.",
                "code": "def search(self, nums: List[int], target: int) -> int:\n"
                        "    left, right = 0, len(nums) - 1\n"
                        "    while left <= right:\n"
                        "        mid = (left + right) // 2\n"
                        "        if nums[mid] == target:\n"
                        "            return mid\n"
                        "        if nums[mid] < target:\n"
                        "            left = mid + 1\n"
                        "        else:\n"
                        "            right = mid - 1\n"
                        "    return -1",
                "why": {
                    "q": "Почему цикл идёт, пока left <= right, а не left < right?",
                    "opts": [
                        "Отрезок [left, right] закрытый: при left == right в нём ещё остаётся один непроверенный элемент",
                        "Так цикл выполняется быстрее",
                        "Иначе mid может выйти за границы массива",
                    ],
                    "ok": 0,
                    "exp": "Оба конца отрезка входят в поиск. Когда left и right совпали, остался ровно один кандидат, и его нужно проверить. Если остановиться раньше, пропустится ответ в последней позиции.",
                },
            },
            {
                "id": "lower_bound",
                "name": "lower_bound",
                "note": "Первая позиция, где значение >= target. Если такого нет, вернёт len(nums).",
                "code": "def lower_bound(self, nums: List[int], target: int) -> int:\n"
                        "    left, right = 0, len(nums)\n"
                        "    while left < right:\n"
                        "        mid = (left + right) // 2\n"
                        "        if nums[mid] < target:\n"
                        "            left = mid + 1\n"
                        "        else:\n"
                        "            right = mid\n"
                        "    return left",
                "why": {
                    "q": "Почему здесь right = len(nums), а не len(nums) - 1?",
                    "opts": [
                        "Ответом может быть позиция сразу за последним элементом, и отрезок должен её включать",
                        "Чтобы mid никогда не равнялся нулю",
                        "Так цикл завершается за меньшее число шагов",
                    ],
                    "ok": 0,
                    "exp": "Отрезок здесь полуоткрытый: [left, right). Если все элементы меньше target, правильный ответ это len(nums), «позиция после конца». Поэтому right стартует с len(nums).",
                },
            },
            {
                "id": "upper_bound",
                "name": "upper_bound",
                "note": "Первая позиция, где значение строго больше target.",
                "code": "def upper_bound(self, nums: List[int], target: int) -> int:\n"
                        "    left, right = 0, len(nums)\n"
                        "    while left < right:\n"
                        "        mid = (left + right) // 2\n"
                        "        if nums[mid] <= target:\n"
                        "            left = mid + 1\n"
                        "        else:\n"
                        "            right = mid\n"
                        "    return left",
                "why": {
                    "q": "Чем upper_bound отличается от lower_bound в коде?",
                    "opts": [
                        "Условием сдвига left: nums[mid] <= target вместо nums[mid] < target",
                        "Начальным значением right",
                        "Тем, что вместо right = mid пишется right = mid - 1",
                    ],
                    "ok": 0,
                    "exp": "Всё остальное совпадает. lower_bound пропускает только элементы меньше target, а upper_bound пропускает и равные ему, поэтому останавливается за последним вхождением.",
                },
            },
        ],
    },
    {
        "id": "bs_range",
        "title": "Первая и последняя позиции элемента",
        "tag": "бинарный поиск · LeetCode 34 · Medium",
        "desc": "Две границы одним шаблоном с флагом.",
        "task": "\n".join([
            "Дан отсортированный по возрастанию массив nums и число target. Найди индексы первого и последнего вхождения target. Если числа в массиве нет, верни [-1, -1]. Нужно решение за O(log n).",
            "Пример: nums = [5, 7, 7, 8, 8, 10], target = 8 → [3, 4].",
            "Пример: nums = [5, 7, 7, 8, 8, 10], target = 6 → [-1, -1].",
            "Сложность: O(log n) по времени, O(1) по памяти.",
        ]),
        "imports": "from typing import List",
        "cls": "class Solution:",
        "blocks": [
            {
                "id": "bound",
                "name": "bound",
                "note": "Одна функция для обеих границ: strict=False даёт lower_bound, strict=True даёт upper_bound.",
                "code": "def bound(self, nums: List[int], target: int, strict: bool) -> int:\n"
                        "    left, right = 0, len(nums)\n"
                        "    while left < right:\n"
                        "        mid = (left + right) // 2\n"
                        "        if nums[mid] < target or (strict and nums[mid] == target):\n"
                        "            left = mid + 1\n"
                        "        else:\n"
                        "            right = mid\n"
                        "    return left",
                "why": {
                    "q": "Зачем один метод с флагом strict вместо двух отдельных функций?",
                    "opts": [
                        "Левая и правая границы отличаются одним условием, остальной код общий",
                        "С флагом бинарный поиск работает быстрее",
                        "Для правой границы нужен другой алгоритм, а флаг его включает",
                    ],
                    "ok": 0,
                    "exp": "Алгоритм один и тот же. Единственная разница: пропускать ли элементы, равные target. Это и переключает флаг, а дублировать цикл незачем.",
                },
            },
            {
                "id": "searchRange",
                "name": "searchRange",
                "note": "Находит обе границы и проверяет, что target вообще есть в массиве.",
                "code": "def searchRange(self, nums: List[int], target: int) -> List[int]:\n"
                        "    first = self.bound(nums, target, False)\n"
                        "    last = self.bound(nums, target, True) - 1\n"
                        "    if first <= last:\n"
                        "        return [first, last]\n"
                        "    return [-1, -1]",
                "why": {
                    "q": "Почему последняя позиция считается как bound(..., True) - 1?",
                    "opts": [
                        "bound со strict=True возвращает позицию сразу после последнего target, поэтому нужно отступить на шаг",
                        "Индексы в Python начинаются с нуля, поэтому всегда вычитаем 1",
                        "Так мы защищаемся от выхода за границы массива",
                    ],
                    "ok": 0,
                    "exp": "upper_bound указывает на первый элемент больше target, то есть за последнее вхождение. Если target нет, first окажется больше last, и условие first <= last вернёт [-1, -1].",
                },
            },
        ],
    },
    {
        "id": "bs_koko",
        "title": "Коко и бананы: поиск по ответу",
        "tag": "бинарный поиск по ответу · LeetCode 875 · Medium",
        "desc": "Бинарный поиск по значению скорости, а не по индексу.",
        "task": "\n".join([
            "Коко любит бананы. Есть кучи piles[i] бананов, охранники вернутся через h часов. За час Коко выбирает одну кучу и съедает из неё k бананов (если в куче меньше k, съедает всю кучу и до конца часа больше не ест). Найди минимальное целое k, при котором она успеет съесть все бананы за h часов.",
            "Пример: piles = [3, 6, 7, 11], h = 8 → 4.",
            "Пример: piles = [30, 11, 23, 4, 20], h = 5 → 30.",
            "Сложность: O(n log m) по времени, где m = max(piles); O(1) по памяти.",
        ]),
        "imports": "from typing import List",
        "cls": "class Solution:",
        "blocks": [
            {
                "id": "hours_needed",
                "name": "hours_needed",
                "note": "Сколько часов уйдёт на все кучи при заданной скорости.",
                "code": "def hours_needed(self, piles: List[int], speed: int) -> int:\n"
                        "    return sum((pile + speed - 1) // speed for pile in piles)",
                "why": {
                    "q": "Зачем писать (pile + speed - 1) // speed?",
                    "opts": [
                        "Это целочисленное деление с округлением вверх: недоеденная куча всё равно занимает целый час",
                        "Так деление выполняется быстрее обычного",
                        "Чтобы избежать деления на ноль",
                    ],
                    "ok": 0,
                    "exp": "Обычное // округляет вниз, а часов нужно столько, сколько потребуется на остаток тоже. Добавка speed - 1 превращает округление вниз в округление вверх.",
                },
            },
            {
                "id": "minEatingSpeed",
                "name": "minEatingSpeed",
                "note": "Ищет наименьшую скорость, при которой hours_needed <= h.",
                "code": "def minEatingSpeed(self, piles: List[int], h: int) -> int:\n"
                        "    left, right = 1, max(piles)\n"
                        "    while left < right:\n"
                        "        mid = (left + right) // 2\n"
                        "        if self.hours_needed(piles, mid) <= h:\n"
                        "            right = mid\n"
                        "        else:\n"
                        "            left = mid + 1\n"
                        "    return left",
                "why": {
                    "q": "Почему при hours_needed <= h мы пишем right = mid, а не mid - 1?",
                    "opts": [
                        "mid уже подходит и может оказаться минимальным подходящим, выбрасывать его нельзя",
                        "Иначе цикл станет бесконечным при нечётной длине отрезка",
                        "Чтобы скорость всегда оставалась чётной",
                    ],
                    "ok": 0,
                    "exp": "Мы ищем первую подходящую скорость. Если mid подходит, ответ либо он сам, либо меньше. Поэтому правую границу ставим в mid, а не мимо него.",
                },
            },
        ],
    },
    {
        "id": "bs_rotated",
        "title": "Поиск в повёрнутом массиве",
        "tag": "бинарный поиск · LeetCode 33 · Medium",
        "desc": "Находим точку разворота, затем ищем в нужной половине.",
        "task": "\n".join([
            "Отсортированный по возрастанию массив с уникальными значениями был циклически сдвинут (например, [0, 1, 2, 4, 5, 6, 7] превратился в [4, 5, 6, 7, 0, 1, 2]). Найди индекс target или верни -1. Нужно решение за O(log n).",
            "Пример: nums = [4, 5, 6, 7, 0, 1, 2], target = 0 → 4.",
            "Пример: nums = [4, 5, 6, 7, 0, 1, 2], target = 3 → -1.",
            "Сложность: O(log n) по времени, O(1) по памяти.",
        ]),
        "imports": "from typing import List",
        "cls": "class Solution:",
        "blocks": [
            {
                "id": "find_min_index",
                "name": "find_min_index",
                "note": "Индекс минимального элемента, то есть точка, где массив «сломан».",
                "code": "def find_min_index(self, nums: List[int]) -> int:\n"
                        "    left, right = 0, len(nums) - 1\n"
                        "    while left < right:\n"
                        "        mid = (left + right) // 2\n"
                        "        if nums[mid] > nums[right]:\n"
                        "            left = mid + 1\n"
                        "        else:\n"
                        "            right = mid\n"
                        "    return left",
                "why": {
                    "q": "Почему mid сравнивают именно с nums[right]?",
                    "opts": [
                        "Если nums[mid] больше nums[right], минимум точно правее mid; иначе он в mid или левее",
                        "Потому что правый элемент всегда самый большой",
                        "Сравнение с nums[left] не работает ни в каком случае",
                    ],
                    "ok": 0,
                    "exp": "В повёрнутом массиве значение посередине больше правого края только тогда, когда разрыв лежит справа от mid. В остальных случаях правая часть отсортирована и минимум не дальше mid.",
                },
            },
            {
                "id": "bsearch",
                "name": "bsearch",
                "note": "Обычный бинарный поиск, но только на отрезке [left, right].",
                "code": "def bsearch(self, nums: List[int], target: int, left: int, right: int) -> int:\n"
                        "    while left <= right:\n"
                        "        mid = (left + right) // 2\n"
                        "        if nums[mid] == target:\n"
                        "            return mid\n"
                        "        if nums[mid] < target:\n"
                        "            left = mid + 1\n"
                        "        else:\n"
                        "            right = mid - 1\n"
                        "    return -1",
                "why": {
                    "q": "Зачем bsearch принимает границы left и right параметрами?",
                    "opts": [
                        "Чтобы искать только в одной из двух отсортированных половин массива",
                        "Чтобы функцию можно было вызвать рекурсивно",
                        "Так Python быстрее работает с аргументами",
                    ],
                    "ok": 0,
                    "exp": "После поиска разворота массив состоит из двух отсортированных кусков. Обычный поиск работает на каждом из них, нужно лишь указать, на каком.",
                },
            },
            {
                "id": "search",
                "name": "search",
                "note": "Определяет, в какой половине лежит target, и ищет там.",
                "code": "def search(self, nums: List[int], target: int) -> int:\n"
                        "    pivot = self.find_min_index(nums)\n"
                        "    if nums[pivot] <= target <= nums[-1]:\n"
                        "        return self.bsearch(nums, target, pivot, len(nums) - 1)\n"
                        "    return self.bsearch(nums, target, 0, pivot - 1)",
                "why": {
                    "q": "Как понять, что target лежит в правой половине (начиная с минимума)?",
                    "opts": [
                        "Он находится между минимумом и последним элементом массива",
                        "Он больше первого элемента массива",
                        "Он чётный",
                    ],
                    "ok": 0,
                    "exp": "Правая половина идёт от минимума до последнего элемента и отсортирована. Если target не попадает в этот диапазон, остаётся только левая половина.",
                },
            },
        ],
    },
    {
        "id": "bs_matrix",
        "title": "Поиск в матрице",
        "tag": "бинарный поиск · LeetCode 74 · Medium",
        "desc": "Матрица как один длинный отсортированный массив.",
        "task": "\n".join([
            "Матрица m × n обладает свойствами: числа в каждой строке отсортированы по возрастанию, а первое число строки больше последнего числа предыдущей строки. Верни True, если target есть в матрице. Нужно решение за O(log(m · n)).",
            "Пример: matrix = [[1, 3, 5, 7], [10, 11, 16, 20], [23, 30, 34, 60]], target = 3 → True.",
            "Пример: тот же matrix, target = 13 → False.",
            "Сложность: O(log(m · n)) по времени, O(1) по памяти.",
        ]),
        "imports": "from typing import List",
        "cls": "class Solution:",
        "blocks": [
            {
                "id": "value_at",
                "name": "value_at",
                "note": "Достаёт элемент по сквозному номеру, как будто матрица вытянута в одну строку.",
                "code": "def value_at(self, matrix: List[List[int]], idx: int) -> int:\n"
                        "    cols = len(matrix[0])\n"
                        "    return matrix[idx // cols][idx % cols]",
                "why": {
                    "q": "Как по сквозному номеру idx найти строку и столбец?",
                    "opts": [
                        "Строка = idx // cols, столбец = idx % cols",
                        "Строка = idx % cols, столбец = idx // cols",
                        "Строка = idx, столбец = 0",
                    ],
                    "ok": 0,
                    "exp": "Целое деление на число столбцов говорит, сколько полных строк уже прошло, а остаток это позиция внутри строки.",
                },
            },
            {
                "id": "searchMatrix",
                "name": "searchMatrix",
                "note": "Обычный бинарный поиск по номерам от 0 до m · n - 1.",
                "code": "def searchMatrix(self, matrix: List[List[int]], target: int) -> bool:\n"
                        "    left, right = 0, len(matrix) * len(matrix[0]) - 1\n"
                        "    while left <= right:\n"
                        "        mid = (left + right) // 2\n"
                        "        value = self.value_at(matrix, mid)\n"
                        "        if value == target:\n"
                        "            return True\n"
                        "        if value < target:\n"
                        "            left = mid + 1\n"
                        "        else:\n"
                        "            right = mid - 1\n"
                        "    return False",
                "why": {
                    "q": "Почему по матрице можно искать бинарным поиском целиком?",
                    "opts": [
                        "Если выписать строки одну за другой, получится один отсортированный массив",
                        "Потому что матрица всегда квадратная",
                        "Потому что в каждом столбце числа тоже отсортированы по убыванию",
                    ],
                    "ok": 0,
                    "exp": "Каждая строка отсортирована, а следующая начинается с большего числа, чем кончилась предыдущая. Значит, сквозная последовательность возрастает, и подходит обычный поиск.",
                },
            },
        ],
    },
]

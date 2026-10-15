"""Задачи алгоритма «Бинарный поиск». Каждая: условие, подсказки, заготовка, эталон и тесты на check()."""


def c(s):
    return s.strip("\n")


HDR = "from typing import List\n\n\nclass Solution:\n"

PROBLEMS_BS = [
    {
        "id": "bs_704", "num": 704, "title": "Бинарный поиск", "level": "easy", "fn": "search",
        "statement": "Дан отсортированный по возрастанию массив nums из различных чисел и число target. Верни индекс target или -1, если его в массиве нет. Нужно решение за O(log n): перебор и nums.index здесь не пройдут.",
        "examples": ["nums = [-1, 0, 3, 5, 9, 12], target = 9  →  4", "nums = [-1, 0, 3, 5, 9, 12], target = 2  →  -1"],
        "hints": [
            "Это шаблон search из урока, один в один: границы [left, right] и цикл while left <= right.",
            "Сравни nums[mid] с target: нашёл, верни mid; меньше, left = mid + 1; больше, right = mid - 1.",
        ],
        "starter": HDR + c('''
    def search(self, nums: List[int], target: int) -> int:
        pass
'''),
        "reference": HDR + c('''
    def search(self, nums: List[int], target: int) -> int:
        left, right = 0, len(nums) - 1
        while left <= right:
            mid = (left + right) // 2
            if nums[mid] == target:
                return mid
            if nums[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return -1
'''),
        "insight": "Ровно шаблон из урока, без изменений. Это разминка: руки должны сами выдать цикл, границы и сдвиги.",
        "pre": "",
        "tests": c('''
def gen(r):
    a = sorted(r.sample(range(-100, 100), r.randint(1, 60)))
    t = r.choice(a) if r.random() < 0.6 else r.randint(-110, 110)
    return (a, t)

def brute(a, t):
    return a.index(t) if t in a else -1

def call(S, a, t):
    return S.search(Guard(a, lim(len(a))), t)

check(S, "search", gen, brute, call=call)
'''),
    },
    {
        "id": "bs_35", "num": 35, "title": "Позиция вставки", "level": "easy", "fn": "searchInsert",
        "statement": "Дан отсортированный массив различных чисел nums и число target. Верни индекс, на котором target лежит в массиве, а если его нет, индекс, куда его нужно вставить, чтобы порядок сохранился. Решение за O(log n).",
        "examples": ["nums = [1, 3, 5, 6], target = 5  →  2", "nums = [1, 3, 5, 6], target = 2  →  1", "nums = [1, 3, 5, 6], target = 7  →  4"],
        "hints": [
            "Это lower_bound из шаблона: первая позиция, где nums[i] >= target.",
            "Границы [left, right) с right = len(nums). Если nums[mid] < target, left = mid + 1, иначе right = mid. Ответ left.",
        ],
        "starter": HDR + c('''
    def searchInsert(self, nums: List[int], target: int) -> int:
        pass
'''),
        "reference": HDR + c('''
    def searchInsert(self, nums: List[int], target: int) -> int:
        left, right = 0, len(nums)
        while left < right:
            mid = (left + right) // 2
            if nums[mid] < target:
                left = mid + 1
            else:
                right = mid
        return left
'''),
        "insight": "Задача и есть lower_bound: позиция вставки совпадает с первой позицией, где элемент не меньше target.",
        "pre": "",
        "tests": c('''
def gen(r):
    a = sorted(r.sample(range(-60, 60), r.randint(1, 50)))
    return (a, r.randint(-65, 65))

def brute(a, t):
    return bisect.bisect_left(a, t)

def call(S, a, t):
    return S.searchInsert(Guard(a, lim(len(a))), t)

check(S, "searchInsert", gen, brute, call=call)
'''),
    },
    {
        "id": "bs_278", "num": 278, "title": "Первая плохая версия", "level": "easy", "fn": "firstBadVersion",
        "statement": "Есть n версий продукта, начиная с 1. Начиная с какой-то версии все следующие плохие. Функция isBadVersion(v) (уже определена, писать не надо) говорит, плохая ли версия v. Найди первую плохую версию, вызвав isBadVersion как можно реже: больше 70 вызовов засчитывается как ошибка.",
        "examples": ["n = 5, первая плохая версия 4  →  4", "n = 1, первая плохая версия 1  →  1"],
        "hints": [
            "Версии идут «хорошие, потом плохие»: условие монотонно. Нужна первая позиция, где предикат истинен, то есть lower_bound по предикату.",
            "Границы [1, n]. Если isBadVersion(mid) истинна, ответ в mid или левее: right = mid. Иначе left = mid + 1.",
        ],
        "starter": HDR.replace("from typing import List\n\n\n", "") + c('''
    def firstBadVersion(self, n: int) -> int:
        # isBadVersion(version) -> bool уже определена за тебя
        pass
'''),
        "reference": c('''
class Solution:
    def firstBadVersion(self, n: int) -> int:
        left, right = 1, n
        while left < right:
            mid = (left + right) // 2
            if isBadVersion(mid):
                right = mid
            else:
                left = mid + 1
        return left
'''),
        "insight": "Вместо сравнения nums[mid] < target теперь вызов isBadVersion(mid). Шаблон lower_bound тот же: предикат вместо сравнения.",
        "pre": c('''
_bad = 1
_calls = 0

def isBadVersion(v):
    global _calls
    _calls += 1
    if _calls > 70:
        raise Fail("Слишком много вызовов isBadVersion (больше 70): нужен бинарный поиск.")
    return v >= _bad
'''),
        "tests": c('''
def gen(r):
    n = r.choice([1, 2, 3, 10, 100, 10 ** 6, 10 ** 9, r.randint(1, 10 ** 9)])
    return (n, r.randint(1, n))

def brute(n, bad):
    return bad

def call(S, n, bad):
    global _bad, _calls
    _bad, _calls = bad, 0
    return S.firstBadVersion(n)

check(S, "firstBadVersion", gen, brute, call=call)
'''),
    },
    {
        "id": "bs_69", "num": 69, "title": "Корень из x", "level": "easy", "fn": "mySqrt",
        "statement": "Дано неотрицательное целое x. Верни целую часть квадратного корня из x (округление вниз). Использовать sqrt, ** 0.5 и math нельзя, решай бинарным поиском.",
        "examples": ["x = 4  →  2", "x = 8  →  2  (корень равен 2.828…, берём 2)"],
        "hints": [
            "Ищем по ответу, а не по массиву: ответ лежит на отрезке [0, x], а условие mid * mid <= x монотонно.",
            "Нужно последнее подходящее mid, поэтому mid округляй вверх: (left + right + 1) // 2. Если mid * mid <= x, left = mid, иначе right = mid - 1.",
        ],
        "starter": c('''
class Solution:
    def mySqrt(self, x: int) -> int:
        pass
'''),
        "reference": c('''
class Solution:
    def mySqrt(self, x: int) -> int:
        left, right = 0, x
        while left < right:
            mid = (left + right + 1) // 2
            if mid * mid <= x:
                left = mid
            else:
                right = mid - 1
        return left
'''),
        "insight": "Бинарный поиск по ответу. Здесь нужно последнее «хорошее» значение, поэтому mid округляется вверх: зеркальный вариант шаблона.",
        "pre": "",
        "tests": c('''
def gen(r):
    return (r.choice([0, 1, 2, 3, 4, 8, 15, 16, 17, r.randint(0, 1000), r.randint(0, 2 ** 31 - 1)]),)

def brute(x):
    return math.isqrt(x)

check(S, "mySqrt", gen, brute)
'''),
    },
    {
        "id": "bs_162", "num": 162, "title": "Пик в массиве", "level": "medium", "fn": "findPeakElement",
        "statement": "Пик это элемент, который строго больше обоих соседей (за краями массива считай минус бесконечность). Дан массив nums, где соседние элементы различны. Верни индекс любого пика. Массив не отсортирован, но решение должно работать за O(log n).",
        "examples": ["nums = [1, 2, 3, 1]  →  2", "nums = [1, 2, 1, 3, 5, 6, 4]  →  1 или 5 (годится любой пик)"],
        "hints": [
            "Бинарный поиск работает и без сортировки: смотри на наклон. Сравнивай nums[mid] и nums[mid + 1].",
            "Если nums[mid] < nums[mid + 1], справа точно есть пик: left = mid + 1. Иначе пик в mid или левее: right = mid.",
        ],
        "starter": HDR + c('''
    def findPeakElement(self, nums: List[int]) -> int:
        pass
'''),
        "reference": HDR + c('''
    def findPeakElement(self, nums: List[int]) -> int:
        left, right = 0, len(nums) - 1
        while left < right:
            mid = (left + right) // 2
            if nums[mid] < nums[mid + 1]:
                left = mid + 1
            else:
                right = mid
        return left
'''),
        "insight": "Условие поиска теперь не «равно target», а «в какую сторону растёт массив». Шаблон [left, right) с right = mid остаётся тем же.",
        "pre": "",
        "tests": c('''
def gen(r):
    a = [r.randint(-50, 50)]
    for _ in range(r.randint(0, 40)):
        x = r.randint(-50, 50)
        while x == a[-1]:
            x = r.randint(-50, 50)
        a.append(x)
    return (a,)

def brute(a):
    n = len(a)
    return {i for i in range(n) if (i == 0 or a[i - 1] < a[i]) and (i == n - 1 or a[i + 1] < a[i])}

def same(got, exp, a):
    return got in exp

def call(S, a):
    return S.findPeakElement(Guard(a, lim(len(a))))

check(S, "findPeakElement", gen, brute, same=same, call=call)
'''),
    },
    {
        "id": "bs_153", "num": 153, "title": "Минимум в повёрнутом массиве", "level": "medium", "fn": "findMin",
        "statement": "Отсортированный по возрастанию массив различных чисел циклически сдвинули, например [0, 1, 2, 4, 5, 6, 7] превратился в [4, 5, 6, 7, 0, 1, 2]. Верни минимальный элемент за O(log n).",
        "examples": ["nums = [3, 4, 5, 1, 2]  →  1", "nums = [4, 5, 6, 7, 0, 1, 2]  →  0", "nums = [11, 13, 15, 17]  →  11"],
        "hints": [
            "Сравни середину с правым краем: если nums[mid] > nums[right], минимум правее mid.",
            "Иначе минимум в mid или левее: right = mid. Цикл while left < right, ответ nums[left].",
        ],
        "starter": HDR + c('''
    def findMin(self, nums: List[int]) -> int:
        pass
'''),
        "reference": HDR + c('''
    def findMin(self, nums: List[int]) -> int:
        left, right = 0, len(nums) - 1
        while left < right:
            mid = (left + right) // 2
            if nums[mid] > nums[right]:
                left = mid + 1
            else:
                right = mid
        return nums[left]
'''),
        "insight": "Это метод find_min_index из урока про повёрнутый массив, только вернуть нужно значение, а не индекс.",
        "pre": "",
        "tests": c('''
def gen(r):
    n = r.randint(1, 30)
    a = sorted(r.sample(range(-60, 60), n))
    k = r.randint(0, n - 1)
    return (a[k:] + a[:k],)

def brute(a):
    return min(a)

def call(S, a):
    return S.findMin(Guard(a, lim(len(a))))

check(S, "findMin", gen, brute, call=call)
'''),
    },
    {
        "id": "bs_540", "num": 540, "title": "Одиночный элемент", "level": "medium", "fn": "singleNonDuplicate",
        "statement": "В отсортированном массиве каждое число встречается дважды, кроме одного, которое встречается один раз. Найди это число за O(log n) и O(1) памяти.",
        "examples": ["nums = [1, 1, 2, 3, 3, 4, 4, 8, 8]  →  2", "nums = [3, 3, 7, 7, 10, 11, 11]  →  10"],
        "hints": [
            "До одиночки пары стоят на индексах (чётный, нечётный), после него сдвигаются: (нечётный, чётный). Это и есть условие для бинарного поиска.",
            "Приведи mid к чётному (если нечётный, mid -= 1). Если nums[mid] == nums[mid + 1], одиночка правее: left = mid + 2. Иначе right = mid.",
        ],
        "starter": HDR + c('''
    def singleNonDuplicate(self, nums: List[int]) -> int:
        pass
'''),
        "reference": HDR + c('''
    def singleNonDuplicate(self, nums: List[int]) -> int:
        left, right = 0, len(nums) - 1
        while left < right:
            mid = (left + right) // 2
            if mid % 2 == 1:
                mid -= 1
            if nums[mid] == nums[mid + 1]:
                left = mid + 2
            else:
                right = mid
        return nums[left]
'''),
        "insight": "Условие поиска ты придумываешь сам: чётность индекса пары. Шаблон и сужение границ остаются прежними.",
        "pre": "",
        "tests": c('''
def gen(r):
    vals = sorted(r.sample(range(-40, 60), r.randint(1, 16)))
    one = r.choice(vals)
    a = []
    for v in vals:
        a += [v] if v == one else [v, v]
    return (a, one)

def brute(a, one):
    return one

def call(S, a, one):
    return S.singleNonDuplicate(Guard(a, lim(len(a))))

check(S, "singleNonDuplicate", gen, brute, call=call)
'''),
    },
    {
        "id": "bs_1011", "num": 1011, "title": "Доставка грузов за D дней", "level": "medium", "fn": "shipWithinDays",
        "statement": "Грузы с весами weights нужно перевезти в том же порядке за days дней. Каждый день на корабль грузят подряд идущие грузы, пока суммарный вес не превысит его вместимость. Найди минимальную вместимость, при которой всё успеют вывезти за days дней.",
        "examples": ["weights = [1,2,3,4,5,6,7,8,9,10], days = 5  →  15", "weights = [3, 2, 2, 4, 1, 4], days = 3  →  6"],
        "hints": [
            "Ищем по ответу: вместимость лежит в [max(weights), sum(weights)], и чем она больше, тем меньше дней нужно.",
            "Напиши проверку «хватит ли days дней при вместимости mid» (жадно), подставь в шаблон: если хватает, right = mid, иначе left = mid + 1.",
        ],
        "starter": HDR + c('''
    def shipWithinDays(self, weights: List[int], days: int) -> int:
        pass
'''),
        "reference": HDR + c('''
    def shipWithinDays(self, weights: List[int], days: int) -> int:
        def days_needed(capacity):
            used, load = 1, 0
            for w in weights:
                if load + w > capacity:
                    used += 1
                    load = 0
                load += w
            return used

        left, right = max(weights), sum(weights)
        while left < right:
            mid = (left + right) // 2
            if days_needed(mid) <= days:
                right = mid
            else:
                left = mid + 1
        return left
'''),
        "insight": "Тот же шаблон, что в уроке про Коку: бинарный поиск по ответу и жадная проверка. Меняется только функция проверки.",
        "pre": "",
        "tests": c('''
def gen(r):
    w = [r.randint(1, 20) for _ in range(r.randint(1, 10))]
    return (w, r.randint(1, len(w)))

def need(w, cap):
    used, load = 1, 0
    for x in w:
        if load + x > cap:
            used += 1
            load = 0
        load += x
    return used

def brute(w, days):
    return next(cap for cap in range(max(w), sum(w) + 1) if need(w, cap) <= days)

check(S, "shipWithinDays", gen, brute)
'''),
    },
    {
        "id": "bs_410", "num": 410, "title": "Разбиение массива с минимальной наибольшей суммой", "level": "hard", "fn": "splitArray",
        "statement": "Дан массив неотрицательных чисел nums и число k. Раздели массив на k непустых подряд идущих частей так, чтобы наибольшая из сумм частей была как можно меньше. Верни эту минимальную наибольшую сумму.",
        "examples": ["nums = [7, 2, 5, 10, 8], k = 2  →  18  (части [7, 2, 5] и [10, 8])", "nums = [1, 2, 3, 4, 5], k = 2  →  9"],
        "hints": [
            "Это «Кока и бананы» в другой обёртке. Ищем по ответу: минимально возможную наибольшую сумму.",
            "Ответ лежит в [max(nums), sum(nums)]. Проверка жадная: набирай часть, пока сумма не превысит mid, потом начинай новую и считай их число. Частей не больше k, значит right = mid, иначе left = mid + 1.",
        ],
        "starter": HDR + c('''
    def splitArray(self, nums: List[int], k: int) -> int:
        pass
'''),
        "reference": HDR + c('''
    def splitArray(self, nums: List[int], k: int) -> int:
        def parts_needed(limit):
            parts, cur = 1, 0
            for x in nums:
                if cur + x > limit:
                    parts += 1
                    cur = 0
                cur += x
            return parts

        left, right = max(nums), sum(nums)
        while left < right:
            mid = (left + right) // 2
            if parts_needed(mid) <= k:
                right = mid
            else:
                left = mid + 1
        return left
'''),
        "insight": "По названию hard, по шаблону та же задача, что про корабль и Коку. Трудно только заметить, что ответ можно искать бинарно.",
        "pre": "",
        "tests": c('''
def gen(r):
    a = [r.randint(0, 20) for _ in range(r.randint(1, 9))]
    return (a, r.randint(1, len(a)))

def brute(a, k):
    n = len(a)
    pre = [0]
    for x in a:
        pre.append(pre[-1] + x)
    INF = float("inf")
    dp = [[INF] * (k + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    for i in range(1, n + 1):
        for j in range(1, min(i, k) + 1):
            for p in range(j - 1, i):
                dp[i][j] = min(dp[i][j], max(dp[p][j - 1], pre[i] - pre[p]))
    return dp[n][k]

check(S, "splitArray", gen, brute)
'''),
    },
    {
        "id": "bs_4", "num": 4, "title": "Медиана двух отсортированных массивов", "level": "hard", "fn": "findMedianSortedArrays",
        "statement": "Даны два отсортированных массива nums1 и nums2. Верни медиану объединённого массива за O(log(min(m, n))). Для чётной общей длины медиана это среднее двух центральных элементов.",
        "examples": ["nums1 = [1, 3], nums2 = [2]  →  2.0", "nums1 = [1, 2], nums2 = [3, 4]  →  2.5"],
        "hints": [
            "Бинарный поиск идёт по разрезу меньшего массива: сколько элементов i берём слева из nums1. Из nums2 слева берём half - i, где half = (m + n + 1) // 2.",
            "Разрез верный, когда каждый левый элемент не больше каждого правого: nums1[i-1] <= nums2[j] и nums2[j-1] <= nums1[i]. Нарушено первое, right = i - 1, второе, left = i + 1. За краями считай минус и плюс бесконечность.",
        ],
        "starter": HDR + c('''
    def findMedianSortedArrays(self, nums1: List[int], nums2: List[int]) -> float:
        pass
'''),
        "reference": HDR + c('''
    def findMedianSortedArrays(self, nums1: List[int], nums2: List[int]) -> float:
        if len(nums1) > len(nums2):
            nums1, nums2 = nums2, nums1
        m, n = len(nums1), len(nums2)
        half = (m + n + 1) // 2
        left, right = 0, m
        while left <= right:
            i = (left + right) // 2
            j = half - i
            a_left = nums1[i - 1] if i > 0 else float("-inf")
            a_right = nums1[i] if i < m else float("inf")
            b_left = nums2[j - 1] if j > 0 else float("-inf")
            b_right = nums2[j] if j < n else float("inf")
            if a_left > b_right:
                right = i - 1
            elif b_left > a_right:
                left = i + 1
            else:
                if (m + n) % 2 == 1:
                    return float(max(a_left, b_left))
                return (max(a_left, b_left) + min(a_right, b_right)) / 2
'''),
        "insight": "Ищем не значение, а позицию разреза. Условие «разрез хороший» монотонно по i, поэтому шаблон бинарного поиска снова подходит.",
        "pre": "",
        "tests": c('''
def gen(r):
    a = sorted(r.randint(-20, 20) for _ in range(r.randint(0, 8)))
    b = sorted(r.randint(-20, 20) for _ in range(r.randint(0 if a else 1, 8)))
    return (a, b)

def brute(a, b):
    s = sorted(a + b)
    m = len(s)
    return float(s[m // 2]) if m % 2 else (s[m // 2 - 1] + s[m // 2]) / 2

def same(got, exp, args):
    return isinstance(got, (int, float)) and abs(got - exp) < 1e-9

check(S, "findMedianSortedArrays", gen, brute, same=same)
'''),
    },
]

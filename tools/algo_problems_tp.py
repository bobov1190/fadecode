"""Задачи алгоритма «Два указателя»."""


def c(s):
    return s.strip("\n")


HDR = "from typing import List\n\n\nclass Solution:\n"

LIST_PRE = c('''
class ListNode:
    def __init__(self, x=0, next=None):
        self.val = x
        self.next = next

def build_list(a):
    head = None
    for x in reversed(a):
        head = ListNode(x, head)
    return head

def to_list(h):
    out = []
    while h is not None and len(out) < 1000:
        out.append(h.val)
        h = h.next
    return out
''')

LIST_NOTE = "# class ListNode:\n#     def __init__(self, x=0, next=None):\n#         self.val = x\n#         self.next = next\n"

PROBLEMS_TP = [
    {
        "id": "tp_283", "num": 283, "title": "Перенеси нули в конец", "level": "easy", "fn": "moveZeroes",
        "statement": "Дан массив nums. Перенеси все нули в его конец, сохранив порядок остальных элементов. Менять массив нужно на месте, без создания второго массива. Функция ничего не возвращает.",
        "examples": ["nums = [0, 1, 0, 3, 12]  →  [1, 3, 12, 0, 0]", "nums = [0]  →  [0]"],
        "hints": [
            "Это шаблон «быстрый и медленный» из remove_duplicates: slow показывает, куда писать следующий нужный элемент.",
            "fast идёт по всему массиву. Встретив ненулевой, поменяй его местами с nums[slow] и сдвинь slow.",
        ],
        "starter": HDR + c('''
    def moveZeroes(self, nums: List[int]) -> None:
        pass
'''),
        "reference": HDR + c('''
    def moveZeroes(self, nums: List[int]) -> None:
        slow = 0
        for fast in range(len(nums)):
            if nums[fast] != 0:
                nums[slow], nums[fast] = nums[fast], nums[slow]
                slow += 1
'''),
        "insight": "remove_duplicates один в один, только условие «оставить» другое, а вместо записи делаем обмен: нули сами уезжают в хвост.",
        "pre": "",
        "tests": c('''
def gen(r):
    return ([r.choice([0, 0, 0, 1, 2, 3, -1, 5]) for _ in range(r.randint(1, 15))],)

def brute(a):
    return [x for x in a if x != 0] + [0] * a.count(0)

def call(S, a):
    S.moveZeroes(a)
    return a

check(S, "moveZeroes", gen, brute, call=call)
'''),
    },
    {
        "id": "tp_977", "num": 977, "title": "Квадраты отсортированного массива", "level": "easy", "fn": "sortedSquares",
        "statement": "Дан отсортированный по возрастанию массив nums (числа могут быть отрицательными). Верни массив квадратов его элементов, тоже отсортированный по возрастанию. Решение за O(n), без сортировки результата.",
        "examples": ["nums = [-4, -1, 0, 3, 10]  →  [0, 1, 9, 16, 100]", "nums = [-7, -3, 2, 3, 11]  →  [4, 9, 9, 49, 121]"],
        "hints": [
            "Самые большие квадраты лежат по краям массива. Поставь указатели на оба конца, как в two_sum_sorted.",
            "Заполняй результат с конца: сравни abs(nums[left]) и abs(nums[right]), больший квадрат запиши на текущую позицию и сдвинь соответствующий указатель.",
        ],
        "starter": HDR + c('''
    def sortedSquares(self, nums: List[int]) -> List[int]:
        pass
'''),
        "reference": HDR + c('''
    def sortedSquares(self, nums: List[int]) -> List[int]:
        n = len(nums)
        result = [0] * n
        left, right = 0, n - 1
        for pos in range(n - 1, -1, -1):
            if abs(nums[left]) > abs(nums[right]):
                result[pos] = nums[left] ** 2
                left += 1
            else:
                result[pos] = nums[right] ** 2
                right -= 1
        return result
'''),
        "insight": "Указатели с краёв, как в шаблоне, но вместо поиска суммы мы собираем ответ с хвоста: самый большой элемент всегда на одном из краёв.",
        "pre": "",
        "tests": c('''
def gen(r):
    return (sorted(r.randint(-10, 10) for _ in range(r.randint(1, 12))),)

def brute(a):
    return sorted(x * x for x in a)

check(S, "sortedSquares", gen, brute)
'''),
    },
    {
        "id": "tp_876", "num": 876, "title": "Середина связного списка", "level": "easy", "fn": "middleNode",
        "statement": "Дана голова односвязного списка. Верни средний узел. Если узлов чётное число, верни второй из двух средних. Пройти список можно только один раз.",
        "examples": ["[1, 2, 3, 4, 5]  →  узел 3 (и дальше 3 → 4 → 5)", "[1, 2, 3, 4, 5, 6]  →  узел 4 (и дальше 4 → 5 → 6)"],
        "hints": [
            "Быстрый и медленный указатели: быстрый шагает по два узла, медленный по одному.",
            "Когда быстрый дошёл до конца (fast или fast.next равен None), медленный стоит в середине.",
        ],
        "starter": "from typing import Optional\n\n" + LIST_NOTE + c('''

class Solution:
    def middleNode(self, head: Optional[ListNode]) -> Optional[ListNode]:
        pass
'''),
        "reference": "from typing import Optional\n\n" + LIST_NOTE + c('''

class Solution:
    def middleNode(self, head: Optional[ListNode]) -> Optional[ListNode]:
        slow = fast = head
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
        return slow
'''),
        "insight": "Те же slow и fast, что в meeting_point из урока про цикл, но без цикла в списке: останавливаемся по концу.",
        "pre": LIST_PRE,
        "tests": c('''
def gen(r):
    return ([r.randint(0, 99) for _ in range(r.randint(1, 12))],)

def brute(a):
    return a[len(a) // 2:]

def call(S, a):
    return to_list(S.middleNode(build_list(a)))

check(S, "middleNode", gen, brute, call=call)
'''),
    },
    {
        "id": "tp_141", "num": 141, "title": "Есть ли цикл в списке", "level": "easy", "fn": "hasCycle",
        "statement": "Дана голова односвязного списка. Верни True, если в списке есть цикл (какой-то узел можно достичь повторно, идя по next), иначе False. Памяти допустимо O(1): без множества посещённых узлов.",
        "examples": ["3 → 2 → 0 → -4, хвост указывает на второй узел  →  True", "1 → 2, хвост указывает на None  →  False"],
        "hints": [
            "Если цикл есть, быстрый указатель рано или поздно догонит медленный внутри цикла.",
            "Двигай slow на 1 шаг, fast на 2. Если они встретились (is), цикл есть. Если fast дошёл до None, цикла нет.",
        ],
        "starter": "from typing import Optional\n\n" + LIST_NOTE + c('''

class Solution:
    def hasCycle(self, head: Optional[ListNode]) -> bool:
        pass
'''),
        "reference": "from typing import Optional\n\n" + LIST_NOTE + c('''

class Solution:
    def hasCycle(self, head: Optional[ListNode]) -> bool:
        slow = fast = head
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
            if slow is fast:
                return True
        return False
'''),
        "insight": "Это первая половина урока про начало цикла (meeting_point): там возвращали узел встречи, здесь достаточно ответа «да или нет».",
        "pre": LIST_PRE + "\n\n" + c('''
def build_cycle(n, pos):
    nodes = [ListNode(i) for i in range(n)]
    for i in range(n - 1):
        nodes[i].next = nodes[i + 1]
    if n and pos >= 0:
        nodes[-1].next = nodes[pos]
    return nodes[0] if nodes else None
'''),
        "tests": c('''
def gen(r):
    n = r.randint(0, 10)
    return (n, -1 if n == 0 else r.randint(-1, n - 1))

def brute(n, pos):
    return pos != -1

def call(S, n, pos):
    return S.hasCycle(build_cycle(n, pos))

check(S, "hasCycle", gen, brute, call=call)
'''),
    },
    {
        "id": "tp_75", "num": 75, "title": "Сортировка цветов", "level": "medium", "fn": "sortColors",
        "statement": "Массив nums состоит из чисел 0, 1 и 2. Отсортируй его на месте за один проход, без sort() и без подсчёта количества каждого числа. Функция ничего не возвращает.",
        "examples": ["nums = [2, 0, 2, 1, 1, 0]  →  [0, 0, 1, 1, 2, 2]", "nums = [2, 0, 1]  →  [0, 1, 2]"],
        "hints": [
            "Три указателя: low это граница нулей, high граница двоек, mid текущий элемент между ними.",
            "0 меняй с nums[low] и двигай low и mid. 1 просто пропускай (mid += 1). 2 меняй с nums[high] и двигай только high: на mid пришёл ещё не проверенный элемент.",
        ],
        "starter": HDR + c('''
    def sortColors(self, nums: List[int]) -> None:
        pass
'''),
        "reference": HDR + c('''
    def sortColors(self, nums: List[int]) -> None:
        low, mid, high = 0, 0, len(nums) - 1
        while mid <= high:
            if nums[mid] == 0:
                nums[low], nums[mid] = nums[mid], nums[low]
                low += 1
                mid += 1
            elif nums[mid] == 1:
                mid += 1
            else:
                nums[mid], nums[high] = nums[high], nums[mid]
                high -= 1
'''),
        "insight": "Развитие указателей с краёв: два края сужаются к середине, а третий указатель просматривает всё между ними.",
        "pre": "",
        "tests": c('''
def gen(r):
    return ([r.randint(0, 2) for _ in range(r.randint(1, 15))],)

def brute(a):
    return sorted(a)

def call(S, a):
    S.sortColors(a)
    return a

check(S, "sortColors", gen, brute, call=call)
'''),
    },
    {
        "id": "tp_680", "num": 680, "title": "Палиндром с одним удалением", "level": "medium", "fn": "validPalindrome",
        "statement": "Дана строка s. Верни True, если она станет палиндромом после удаления не более одного символа.",
        "examples": ["s = \"aba\"  →  True", "s = \"abca\"  →  True  (удаляем c или b)", "s = \"abc\"  →  False"],
        "hints": [
            "Шаблон is_palindrome: два указателя с краёв идут навстречу. Но на первом несовпадении появляется выбор, какую букву удалить.",
            "Не угадывай: проверь обе ветки, пропустив левую букву или пропустив правую. Для этого вынеси проверку подстроки s[l..r] в отдельную функцию.",
        ],
        "starter": c('''
class Solution:
    def validPalindrome(self, s: str) -> bool:
        pass
'''),
        "reference": c('''
class Solution:
    def validPalindrome(self, s: str) -> bool:
        def is_pal(left, right):
            while left < right:
                if s[left] != s[right]:
                    return False
                left += 1
                right -= 1
            return True

        left, right = 0, len(s) - 1
        while left < right:
            if s[left] != s[right]:
                return is_pal(left + 1, right) or is_pal(left, right - 1)
            left += 1
            right -= 1
        return True
'''),
        "insight": "Шаблон палиндрома плюс одно «право на ошибку»: на несовпадении запускаем две проверки вместо одной.",
        "pre": "",
        "tests": c('''
def gen(r):
    return ("".join(r.choice("abc") for _ in range(r.randint(1, 9))),)

def brute(s):
    return s == s[::-1] or any((s[:i] + s[i + 1:]) == (s[:i] + s[i + 1:])[::-1] for i in range(len(s)))

check(S, "validPalindrome", gen, brute)
'''),
    },
    {
        "id": "tp_881", "num": 881, "title": "Лодки для спасения", "level": "medium", "fn": "numRescueBoats",
        "statement": "people[i] это вес i-го человека, limit это грузоподъёмность лодки. В лодку помещается не больше двух человек, и их суммарный вес не должен превышать limit. Каждый человек весит не больше limit. Найди минимальное число лодок.",
        "examples": ["people = [1, 2], limit = 3  →  1", "people = [3, 2, 2, 1], limit = 3  →  3", "people = [3, 5, 3, 4], limit = 5  →  4"],
        "hints": [
            "Отсортируй людей и поставь указатели на самого лёгкого и самого тяжёлого, как в two_sum_sorted.",
            "Самый тяжёлый поплывёт в любом случае. Если с ним помещается самый лёгкий, возьми обоих (left += 1). Потом right -= 1 и посчитай лодку.",
        ],
        "starter": HDR + c('''
    def numRescueBoats(self, people: List[int], limit: int) -> int:
        pass
'''),
        "reference": HDR + c('''
    def numRescueBoats(self, people: List[int], limit: int) -> int:
        people.sort()
        left, right = 0, len(people) - 1
        boats = 0
        while left <= right:
            if people[left] + people[right] <= limit:
                left += 1
            right -= 1
            boats += 1
        return boats
'''),
        "insight": "Указатели с краёв, как в two_sum_sorted: сравниваем сумму пары с лимитом, только вместо поиска равенства считаем лодки.",
        "pre": "",
        "tests": c('''
def gen(r):
    limit = r.randint(5, 15)
    return ([r.randint(1, limit) for _ in range(r.randint(1, 8))], limit)

def brute(p, limit):
    n = len(p)
    full = (1 << n) - 1

    @functools.lru_cache(None)
    def f(mask):
        if mask == full:
            return 0
        i = 0
        while mask >> i & 1:
            i += 1
        best = 1 + f(mask | 1 << i)
        for j in range(i + 1, n):
            if not mask >> j & 1 and p[i] + p[j] <= limit:
                best = min(best, 1 + f(mask | 1 << i | 1 << j))
        return best

    return f(0)

check(S, "numRescueBoats", gen, brute)
'''),
    },
    {
        "id": "tp_16", "num": 16, "title": "Три числа с ближайшей суммой", "level": "medium", "fn": "threeSumClosest",
        "statement": "Дан массив nums из n >= 3 чисел и число target. Найди три числа, сумма которых ближе всего к target, и верни эту сумму.",
        "examples": ["nums = [-1, 2, 1, -4], target = 1  →  2", "nums = [0, 0, 0], target = 1  →  0"],
        "hints": [
            "Каркас из урока про три числа: сортировка, фиксируем первое число, два указателя на остаток.",
            "Двигай указатели по знаку total - target, как в two_sum_sorted. Запоминай сумму, которая ближе всего к target. Точное совпадение можно вернуть сразу.",
        ],
        "starter": HDR + c('''
    def threeSumClosest(self, nums: List[int], target: int) -> int:
        pass
'''),
        "reference": HDR + c('''
    def threeSumClosest(self, nums: List[int], target: int) -> int:
        nums.sort()
        best = nums[0] + nums[1] + nums[2]
        for i in range(len(nums) - 2):
            left, right = i + 1, len(nums) - 1
            while left < right:
                total = nums[i] + nums[left] + nums[right]
                if abs(total - target) < abs(best - target):
                    best = total
                if total < target:
                    left += 1
                elif total > target:
                    right -= 1
                else:
                    return total
        return best
'''),
        "insight": "Тот же каркас, что у threeSum, но вместо условия «сумма равна нулю» ты следишь за лучшей суммой.",
        "pre": "",
        "tests": c('''
def gen(r):
    return ([r.randint(-20, 20) for _ in range(r.randint(3, 9))], r.randint(-30, 30))

def brute(a, t):
    return min((sum(c) for c in itertools.combinations(a, 3)), key=lambda s: abs(s - t))

def same(got, exp, args):
    a, t = args
    return got in {sum(c) for c in itertools.combinations(a, 3)} and abs(got - t) == abs(exp - t)

check(S, "threeSumClosest", gen, brute, same=same)
'''),
    },
    {
        "id": "tp_633", "num": 633, "title": "Сумма двух квадратов", "level": "medium", "fn": "judgeSquareSum",
        "statement": "Дано неотрицательное целое c. Верни True, если существуют целые неотрицательные a и b, что a² + b² = c.",
        "examples": ["c = 5  →  True  (1² + 2²)", "c = 3  →  False"],
        "hints": [
            "Массива нет, но он воображаемый: числа 0, 1, 2, …, sqrt(c). Поставь два указателя с краёв, как в two_sum_sorted.",
            "left = 0, right = целый корень из c. Сравни left² + right² с c: мало, left += 1; много, right -= 1.",
        ],
        "starter": c('''
import math


class Solution:
    def judgeSquareSum(self, c: int) -> bool:
        pass
'''),
        "reference": c('''
import math


class Solution:
    def judgeSquareSum(self, c: int) -> bool:
        left, right = 0, math.isqrt(c)
        while left <= right:
            total = left * left + right * right
            if total == c:
                return True
            if total < c:
                left += 1
            else:
                right -= 1
        return False
'''),
        "insight": "Два указателя работают и без реального массива: достаточно, чтобы значение монотонно росло с индексом.",
        "pre": "",
        "tests": c('''
def gen(r):
    return (r.choice([0, 1, 2, 3, 4, 5, r.randint(0, 200), r.randint(0, 100000)]),)

def brute(c):
    return any(math.isqrt(c - a * a) ** 2 == c - a * a for a in range(math.isqrt(c) + 1))

check(S, "judgeSquareSum", gen, brute)
'''),
    },
    {
        "id": "tp_19", "num": 19, "title": "Удалить n-й узел с конца", "level": "medium", "fn": "removeNthFromEnd",
        "statement": "Дана голова односвязного списка и число n. Удали n-й узел с конца и верни голову списка. Пройти список нужно за один проход.",
        "examples": ["[1, 2, 3, 4, 5], n = 2  →  [1, 2, 3, 5]", "[1], n = 1  →  []", "[1, 2], n = 1  →  [1]"],
        "hints": [
            "Нужны два указателя с зазором в n узлов между ними. Когда передний у конца, задний стоит у нужного места.",
            "Заведи фиктивный узел перед головой, чтобы удаление головы не было особым случаем. Сначала продвинь fast на n шагов, затем двигай оба, пока fast.next не станет None.",
        ],
        "starter": "from typing import Optional\n\n" + LIST_NOTE + c('''

class Solution:
    def removeNthFromEnd(self, head: Optional[ListNode], n: int) -> Optional[ListNode]:
        pass
'''),
        "reference": "from typing import Optional\n\n" + LIST_NOTE + c('''

class Solution:
    def removeNthFromEnd(self, head: Optional[ListNode], n: int) -> Optional[ListNode]:
        dummy = ListNode(0, head)
        fast = slow = dummy
        for _ in range(n):
            fast = fast.next
        while fast.next:
            fast = fast.next
            slow = slow.next
        slow.next = slow.next.next
        return dummy.next
'''),
        "insight": "Указатели ходят с одинаковой скоростью, но стартуют с разных мест. Зазор вместо разной скорости, как в slow и fast.",
        "pre": LIST_PRE,
        "tests": c('''
def gen(r):
    a = [r.randint(0, 99) for _ in range(r.randint(1, 10))]
    return (a, r.randint(1, len(a)))

def brute(a, n):
    return a[:len(a) - n] + a[len(a) - n + 1:]

def call(S, a, n):
    return to_list(S.removeNthFromEnd(build_list(a), n))

check(S, "removeNthFromEnd", gen, brute, call=call)
'''),
    },
    {
        "id": "tp_76", "num": 76, "title": "Минимальное окно с нужными символами", "level": "hard", "fn": "minWindow",
        "statement": "Даны строки s и t. Верни самую короткую подстроку s, в которой есть все символы t (с учётом повторов). Если такой подстроки нет, верни пустую строку.",
        "examples": ["s = \"ADOBECODEBANC\", t = \"ABC\"  →  \"BANC\"", "s = \"a\", t = \"aa\"  →  \"\""],
        "hints": [
            "Скользящее окно: правый указатель расширяет окно, левый его сжимает. Это два указателя, идущие в одну сторону.",
            "Веди счётчик нужных букв и число ещё не покрытых. Когда окно покрывает t (missing == 0), запомни ответ и двигай left, пока окно остаётся валидным.",
        ],
        "starter": c('''
from collections import Counter


class Solution:
    def minWindow(self, s: str, t: str) -> str:
        pass
'''),
        "reference": c('''
from collections import Counter


class Solution:
    def minWindow(self, s: str, t: str) -> str:
        need = Counter(t)
        missing = len(t)
        best = ""
        left = 0
        for right, ch in enumerate(s):
            if need[ch] > 0:
                missing -= 1
            need[ch] -= 1
            while missing == 0:
                if not best or right - left + 1 < len(best):
                    best = s[left:right + 1]
                need[s[left]] += 1
                if need[s[left]] > 0:
                    missing += 1
                left += 1
        return best
'''),
        "insight": "Указатели идут в одну сторону, как slow и fast, но роли другие: right расширяет окно, left сжимает. Это скользящее окно.",
        "pre": "",
        "tests": c('''
def gen(r):
    return ("".join(r.choice("ABC") for _ in range(r.randint(1, 10))), "".join(r.choice("ABC") for _ in range(r.randint(1, 4))))

def covers(w, t):
    have = collections.Counter(w)
    return all(have[k] >= v for k, v in collections.Counter(t).items())

def brute(s, t):
    best = ""
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            w = s[i:j]
            if covers(w, t) and (best == "" or len(w) < len(best)):
                best = w
    return best

def same(got, exp, args):
    s, t = args
    return isinstance(got, str) and len(got) == len(exp) and (got == "" or (got in s and covers(got, t)))

check(S, "minWindow", gen, brute, same=same)
'''),
    },
]

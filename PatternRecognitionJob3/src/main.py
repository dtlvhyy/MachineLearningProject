from sklearn.svm import SVC
from sklearn.metrics import roc_auc_score
import numpy as np
import os
import xlrd
from random import randint, random

_fname = "作业数据_2017And2016.xls"
_selected_cols = (1, 3, 4, 6, 7, 8, 9)
_ncols = len(_selected_cols)


def read_excel(fname=_fname):
    cwd = os.getcwd()
    if not cwd.endswith("\\src"):
        return
    fpath = cwd.replace("\\src", "\\resource\\") + fname
    book = xlrd.open_workbook(fpath)
    sheet = book.sheet_by_index(0)
    nrows = sheet.nrows
    ncols = sheet.ncols
    data = []
    row = []
    for i in range(1, nrows):
        for j in _selected_cols:
            row.append(sheet.cell(i, j).value)
        data.append(row)
        row = []
    return data


def get_boys_and_girls(data):
    boys = []
    girls = []
    for row in data:
        if row[0] == 1:
            boys.append(row)
        else:
            girls.append(row)
    return boys, girls


def regulate(data, cols):
    nrow = len(data)
    for col in cols:
        l_max = -100000
        l_min = 1000000
        for i in np.arange(nrow):
            if data[i][col] > l_max:
                l_max = data[i][col]
            if data[i][col] < l_min:
                l_min = data[i][col]
        delta = l_max - l_min
        for i in np.arange(nrow):
            data[i][col] = (data[i][col] - l_min) / delta


def check_row(row, ncols=_ncols):
    if row is None:
        return False
    if type(row) != list:
        return False
    if len(row) != ncols:
        return False
    for item in row:
        if item is None or item == '':
            return False
    return True


def do_pretreatment(data):
    if data is None:
        return
    for row in data:
        if check_row(row) is False:
            data.remove(row)


def split_sample(data, ratio):
    if ratio <= 0 or ratio >= 1:
        return None
    from random import randint
    boys = []
    girls = []
    for row in data:
        if row[0] == 1:
            boys.append(row)
        else:
            girls.append(row)
    nboys = len(boys)
    ngirls = len(girls)
    n = int(np.round(nboys * ratio))
    m = int(np.round(ngirls * ratio))
    train_set = []
    test_set = []
    for i in range(n):
        index = randint(0, len(boys) - 1)
        train_set.append(boys[index])
        boys.pop(index)
    for i in range(m):
        index = randint(0, len(girls) - 1)
        train_set.append(girls[index])
        girls.pop(index)
    test_set.extend(boys)
    test_set.extend(girls)
    return train_set, test_set


class ChromosomeWidthError(Exception):
    pass


class Individual:
    __chromosome_width = len(_selected_cols) - 1  # 基因长度 去除男女标志位
    fitness = 0

    def get_chromosome_width(self):
        return self.__chromosome_width

    def __init__(self, str_crm="000000"):
        if type(str_crm) is not str or len(str_crm) is not self.__chromosome_width:
            raise ChromosomeWidthError("Wrong width num")
        temp = []
        for c in str_crm:
            temp.append(int(c))
        self.chromosome = temp

    def get_random_chromosome(self):
        str_crm = ""
        for i in range(self.__chromosome_width):
            str_crm += str(randint(0, 1))
        return str_crm

    def calculate_fitness(self, boys, girls):
        s_boys, s_girls = [], []
        for boy in boys:
            temp = []
            for i in range(self.__chromosome_width):
                if self.chromosome[i]:
                    temp.append(boy[i + 1])  # boy的一个元素不是特征是男女标志位
            s_boys.append(temp)
        for girl in girls:
            temp = []
            for i in range(self.__chromosome_width):
                if self.chromosome[i]:
                    temp.append(girl[i + 1])  # boy的一个元素不是特征是男女标志位
            s_girls.append(temp)
        m_boys = np.matrix(s_boys)
        m_girls = np.matrix(s_girls)
        mean_boys = m_boys.mean(0)  # m_boys行向量的均值
        mean_girls = m_girls.mean(0)  # m_girls行向量的均值
        mean_all = np.row_stack((m_boys, m_girls)).mean(0)  # 总体行向量的均值
        used_dight_num = sum(self.chromosome)
        Sw = np.zeros((used_dight_num, used_dight_num))
        Sb = np.zeros((used_dight_num, used_dight_num))
        for group, mean in ((m_boys, mean_boys), (m_girls, mean_girls)):
            temp = np.zeros((used_dight_num, used_dight_num))
            for a in group:
                delta1 = a - mean
                temp += delta1.T * delta1
            # temp /= len(group)
            # Sw += len(group) / (len(m_boys) + len(m_girls)) * temp
            Sw += 1 / (len(m_boys) + len(m_girls)) * temp
            delta2 = mean - mean_all
            Sb += len(group) / (len(m_boys) + len(m_girls)) * delta2.T * delta2
        fitness = Sb.trace() / (Sw.trace() + 1e-4)  # +1e-4以免分母过小
        self.fitness = fitness
        return fitness


class Group:
    _group = []
    __recombine_digit = (randint(0, Individual().get_chromosome_width() / 2),
                         randint(Individual().get_chromosome_width() / 2, Individual().get_chromosome_width() - 1))
    __mutation_probability = 0.001
    __MAX_TURN = 1000
    __THRESHOLD = 1e-6

    def __init__(self, individual_num=10):
        for i in range(individual_num):
            self._group.append(Individual(Individual().get_random_chromosome()))

    def _round_select(self, boys, girls):
        fitness_list = []
        for individual in self._group:
            fitness_list.append(individual.calculate_fitness(boys, girls))
        fitness_sum = sum(fitness_list)
        probability_list = [x / fitness_sum for x in fitness_list]
        new_group = []
        for i in range(len(self._group)):
            p = random()
            count = 0
            while p > 0:
                p -= probability_list[count]
                count += 1
            count -= 1
            new_group.append(self._group[count])
        return new_group

    def recombine(self, boys, girls):
        evolution_group = self._round_select(boys, girls)
        self._group = evolution_group

    def crossover(self):
        index = 0
        while index < len(self._group):
            recombine_digit = (randint(0, Individual().get_chromosome_width() / 2),
                               randint(Individual().get_chromosome_width() / 2,
                                       Individual().get_chromosome_width() - 1))
            # 上面的代码实现交换位随机
            # recombine_digit = self.__recombine_digit
            for digit in recombine_digit:
                temp = self._group[index].chromosome[digit]
                self._group[index].chromosome[digit] = self._group[index + 1].chromosome[digit]
                self._group[index + 1].chromosome[digit] = temp
            index += 2

    def mutate(self):
        chromosome_width = Individual().get_chromosome_width()
        for index in range(len(self._group)):
            for digit in range(chromosome_width):
                r = random()
                if r < self.__mutation_probability:
                    self._group[index].chromosome[digit] = 1 - self._group[index].chromosome[digit]

    def evolve(self, boys, girls):
        count = 0
        pre_fitness_list = np.zeros((1, len(self._group)))
        while count < self.__MAX_TURN:
            self.recombine(boys, girls)
            self.crossover()
            self.mutate()
            fitness_list = np.matrix([self._group[i].fitness for i in range(len(self._group))])
            delta_list = fitness_list - pre_fitness_list
            delta_list.sort(1)
            delta = sum(delta_list * delta_list.T)[0, 0]
            if delta < self.__THRESHOLD:
                # print("OUT")
                break
            pre_fitness_list = fitness_list
            count += 1
        max_fitness = -1
        flag = 0
        for i in range(len(self._group)):
            if self._group[i].fitness > max_fitness:
                max_fitness = self._group[i].fitness
                flag = i
        # print(self._group[flag].chromosome)
        return self._group[flag].chromosome


def GA():
    data = read_excel()
    do_pretreatment(data)
    # regulate(data, (1, 2))

    # for i in range(10):
    #     print(str.format("#{}: ", str(i)), end="")
    #     group = Group(20)
    #     group.evolve(boys, girls)


    # GA特征选择
    boys, girls = get_boys_and_girls(data)
    group = Group(20)
    fits_well_chromosome = group.evolve(boys, girls)
    print(str.format("Chromosome:{}", str.join("", [str(s) for s in fits_well_chromosome])))
    selected_cols = [0]  # 预先选出男女标志位
    for i in range(len(fits_well_chromosome)):
        if fits_well_chromosome[i]:
            selected_cols.append(i + 1)  # _seleted_cols 第一个元素是男女标志位
    # print(selected_cols)

    # 用GA特征选择选出的特征来筛选列
    GAdata = []
    for row in data:
        temp = []
        for i in selected_cols:
            temp.append(row[i])
        GAdata.append(temp)

    # SVM训练
    train_set, test_set = split_sample(GAdata, 2 / 3)
    X1 = []
    Y1 = []
    for row in train_set:
        X1.append(row[1:])
        Y1.append(row[0])
    clf = SVC(kernel='linear')
    clf.fit(X1, Y1)
    original = []
    output = []
    count, TP, FN, FP, TN = 0, 0, 0, 0, 0
    for row in test_set:
        estimation = clf.predict([row[1:]])[0]
        real = row[0]
        original.append(real)
        output.append(estimation)
        # print(str.format("Real:{} Estimation:{}", real, estimation))
        if real == 1 and estimation == 1:
            TP += 1
        elif real == 1 and estimation == 0:
            FN += 1
        elif real == 0 and estimation == 0:
            TN += 1
        elif real == 0 and estimation == 1:
            FP += 1
        if real == estimation:
            count += 1
    if TP + FN:
        SE = TP / (TP + FN)
    else:
        SE = 0
    if TN + FP:
        SP = TN / (TN + FP)
    else:
        SP = 0
    auc = roc_auc_score(original, output)
    print("SE:", SE)
    print("SP:", SP)
    print("Accuracy:", count / len(test_set))
    print('AUC:', auc)


def PCA():
    import matplotlib.pyplot as plt
    from sklearn.decomposition import PCA
    from mpl_toolkits.mplot3d import Axes3D
    data = read_excel()
    do_pretreatment(data)
    lable = []
    for row in data:
        lable.append(row.pop(0))
    pca = PCA(n_components=3)
    pca.fit(data)
    # print(pca.explained_variance_ratio_)
    # print(pca.explained_variance_)
    newdata = pca.transform(data)
    # fig = plt.figure()
    # ax = Axes3D(fig, rect=[0, 0, 1, 1], elev=30, azim=20)
    # plt.scatter(newdata[:, 0], newdata[:, 1], newdata[:, 2], marker='o')
    # plt.show()
    clf = SVC(kernel='linear')
    clf.fit(newdata, lable)
    SVMDdata = []
    for i in range(len(newdata)):
        temp = []
        temp.append(lable[i])
        temp.extend(newdata[i])
        SVMDdata.append(temp)
    train_set, test_set = split_sample(SVMDdata, 2 / 3)
    original = []
    output = []
    count, TP, FN, FP, TN = 0, 0, 0, 0, 0
    for row in test_set:
        estimation = clf.predict([row[1:]])[0]
        real = row[0]
        original.append(real)
        output.append(estimation)
        # print(str.format("Real:{} Estimation:{}", real, estimation))
        if real == 1 and estimation == 1:
            TP += 1
        elif real == 1 and estimation == 0:
            FN += 1
        elif real == 0 and estimation == 0:
            TN += 1
        elif real == 0 and estimation == 1:
            FP += 1
        if real == estimation:
            count += 1
    if TP + FN:
        SE = TP / (TP + FN)
    else:
        SE = 0
    if TN + FP:
        SP = TN / (TN + FP)
    else:
        SP = 0
    auc = roc_auc_score(original, output)
    print("SE:", SE)
    print("SP:", SP)
    print("Accuracy:", count / len(test_set))
    print('AUC:', auc)


if __name__ == "__main__":
    PCA()

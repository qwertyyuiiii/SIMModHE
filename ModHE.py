import math


class ASIC:
    F = 10 ** 9
    BD = 2048    # Gb/s
    m_bits = 20
    PE_R = 8

    MMtime = 0
    MAtime = 0
    Keyswitchtime = 0
    Relineartime = 0
    Rotatetime = 0
    NTT_time = 0
    # Sdtime = 0
    # Rvtime = 0
    # Comtime = 0
    # SQMtime = 0
    # SEtime = 0

    P_DTU = 0
    P_HBM = 31.8
    P_NTT = 40.2
    P_MM = 11.6
    P_MA = 1.18
    P_Auto = 0.78
    P_SE = 1.96
    # P_SQM = 18.047

    def __init__(self, id):
        self.c_id = id
        self.MMtime = 0
        self.MAtime = 0
        self.multiplytime = 0
        self.rankredtime = 0
        self.NTTtime = 0
        self.Sdtime = 0
        self.Rvtime = 0
        self.Comtime = 0
        return

    # MMtimepe单元顺序计算l个RNS时间，MM完整时间要*self.PE_R^2
    # 模加时间+1，r个延后2r-2
    def multiply_pe(self, N, E, l, R, r, NUM=1, inner=1):
        N1 = N / self.PE_R
        acc_2 = math.pow(2, self.PE_R / R - 1)
        acc_4 = math.pow(4, R / r - 1)
        g = math.ceil(N1/(E * acc_2 * acc_4))
        self.MMtime += (g * l * inner + 3)*math.pow(self.PE_R + 1, 2) / self.F * NUM
        return math.ceil(g * l + 3 + 2*r - 2) / self.F * NUM

    # 乘累加 乘3 加1 r*(r+1)/2间加法1 总共 5
    def multiply_add(self, N, E, l, R, r, NUM=1, inner=1):
        N1 = N / self.PE_R
        acc_2 = math.pow(2, self.PE_R / R - 1)
        acc_4 = math.pow(4, R / r - 1)
        g = math.ceil(N1 / (E * acc_2 * acc_4))
        self.MMtime += (g * l + 3) * inner / self.F * NUM
        self.MAtime += (g * l + 1) * inner / self.F * NUM
        return math.ceil(g + 4 + 1) / self.F * NUM

    def add_plain(self, N, E, l, R, r, NUM=1, inner=1):
        g = math.ceil(N / R / 256)
        self.MAtime += (g * l + 1) * inner / self.F * NUM
        return math.ceil(g + 1) / self.F * NUM

    def mod_up(self, N, E, l, R, r, NUM=1, inner=1): # need to check
        # N1 = N / self.PE_R
        # acc_2 = math.pow(2, self.PE_R / R - 1)
        # acc_4 = math.pow(4, R / r - 1)
        # g = math.ceil(N1 / (E * acc_2 * acc_4))
        g = math.ceil(N / R / E)
        return math.ceil(g + 1) / self.F * NUM

    def mod_down(self, N, E, l, R, r, NUM=1, inner=1): # need to check
        # N1 = N / self.PE_R
        # acc_2 = math.pow(2, self.PE_R / R - 1)
        # acc_4 = math.pow(4, R / r - 1)
        g = math.ceil(N/R / 32)
        self.MAtime += (g * l + 1) * inner / self.F * NUM
        self.MMtime += (g * l + 3) * inner / self.F * NUM
        return self.mod_up(N, E, l, R, NUM, inner) + math.ceil(g * l + 4) / self.F * NUM

    def ntt(self, N, E, l, R, r, NUM=1, inner=1): # need to check
        time = 0
        num = math.log2(N/R)
        time += l * inner * num * N/R/256 * 5 / self.F * NUM
        self.NTTtime += time
        return math.ceil(num * 5) / self.F * NUM

    def multiply(self, N, E, l, R, r, NUM=1):
        alpha = 1
        DNUM = l
        time = self.multiply_pe(N, E, l, R, r, NUM) + \
               self.ntt(N, E, l, R, r, NUM, inner = (r*(r+1) / 2)) + \
               self.mod_up(N, E, l, R, r, NUM, inner=DNUM*(r*(r+1) / 2)) + \
               self.ntt(N, E, l, R, r, NUM, inner=DNUM*(r*(r+1) / 2)) + \
               self.multiply_add(N, E, l, R, r, NUM*(r+1), inner=(r*(r+1)/2)*math.pow(4, R / r - 1))*(DNUM+1) + \
               self.ntt(N, E, 1, R, r, NUM*(l+1)*(r+1), inner=1) + \
               self.mod_down(N, E, l, R, r, NUM*(r+1), inner=1) + \
               self.ntt(N, E, l, R, r, NUM*(r+1), inner=1) + \
               self.add_plain(N, E, l, R, r, NUM=NUM * (r + 1))
        self.multiplytime += time
        return time
        # return 1 / 0.48 * NUM * inner

    # 并行l个INTT时间 + (l-1)个分别ModDown + 并行的l个NTT 进行r+1次
    def rescale(self, N, E, l, R, r, NUM=1):
        time = self.ntt(N, E, l, R, r, NUM*(r+1), inner=1) + \
               self.mod_down(N, E, l-1, R, r, NUM*(r+1)) + \
               self.ntt(N, E, l-1, R, r, NUM*(r+1), inner=1)
        return time

    def rankred(self, N, E, l, R, r, NUM=1):
        alpha = 1
        DNUM = l
        r1 = r/2
        N1 = N / self.PE_R
        acc_2 = math.pow(2, self.PE_R / R - 1)
        acc_4 = math.pow(4, R / r1 - 1)
        g = math.ceil(N1 / (E * acc_2 * acc_4))
        time = math.ceil(g*(l-1)) / self.F * NUM + \
               self.ntt(N, E, l, R, r1, NUM, inner=r1) + \
               self.mod_up(N, E, l, R, r1, NUM, inner=DNUM * r1) + \
               self.ntt(N, E, l, R, r1, NUM, inner=DNUM * r1) + \
               self.multiply_add(N, E, l, R, r1, NUM * (r1 + 1), inner=(r1*math.pow(4, R / r1 - 1))*(DNUM+1)) + \
               self.ntt(N, E, 1, R, r1, NUM * (l+1) * (r1 + 1), inner=1) + \
               self.mod_down(N, E, l, R, r1, NUM * (r1 + 1), inner=1) + \
               self.ntt(N, E, l, R, r1, NUM * (r1 + 1), inner=1) + \
               self.add_plain(N, E, l, R, r1, NUM=NUM * (r1 + 1))
        self.rankredtime += time
        return time

    def keyswitch(self, N, E, l, R, r, NUM=1):
        alpha = 1
        DNUM = l
        N1 = N / self.PE_R
        acc_2 = math.pow(2, self.PE_R / R - 1)
        acc_4 = math.pow(4, R / r - 1)
        g = math.ceil(N1 / (E * acc_2 * acc_4))
        time = math.ceil(g * (l - 1)) / self.F * NUM + \
               self.ntt(N, E, l, R, r, NUM, inner=r) + \
               self.mod_up(N, E, l, R, r, NUM, inner=DNUM * r) + \
               self.ntt(N, E, l, R, r, NUM, inner=DNUM * r) + \
               self.multiply_add(N, E, l, R, r, NUM * (r + 1), inner=(r * math.pow(4, R / r - 1)) * (DNUM + 1)) + \
               self.ntt(N, E, 1, R, r, NUM * (l + 1) * (r + 1), inner=1) + \
               self.mod_down(N, E, l, R, r, NUM * (r + 1), inner=1) + \
               self.ntt(N, E, l, R, r, NUM * (r + 1), inner=1) + \
               self.add_plain(N, E, l, R, r, NUM=NUM * (r + 1))
        return time

    def rotate(self, N, E, l, R, r, NUM=1):
        N1 = N/R
        g = N1/E
        time = math.ceil(g*l + 3 + 1) / self.F * NUM
        self.Rotatetime += time
        return time + self.keyswitch(N, E, l, R, r, NUM)

    def multiply_constant(self, N, E, l, R, r, NUM=1, inner=1):
        N1 = N / self.PE_R
        acc_2 = math.pow(2, self.PE_R / R - 1)
        acc_4 = math.pow(4, R / r - 1)
        g = math.ceil(N1 / (E * acc_2 * acc_4))
        self.MMtime += (g * l * inner + 3) * r * math.pow(4, R / r - 1) / self.F * NUM
        return math.ceil(g * l * inner + 3) / self.F * NUM

    def add_constant(self, N, E, l, R, r, NUM=1, inner=1):
        N1 = N / self.PE_R
        acc_2 = math.pow(2, self.PE_R / R - 1)
        acc_4 = math.pow(4, R / r - 1)
        g = math.ceil(N1 / (E * acc_2 * acc_4))
        self.MAtime += (g * l * inner + 1) * r * math.pow(4, R / r - 1) / self.F * NUM
        return math.ceil(g * l * inner + 1) / self.F * NUM

    def Energy(self):
        NTT_Energy = self.NTTtime * self.P_NTT
        MM_Energy = self.MMtime * self.P_MM
        MA_Energy = self.MAtime * self.P_MA
        Auto_Energy = self.Rotatetime * self.P_Auto
        total = NTT_Energy + MM_Energy + MA_Energy + Auto_Energy
        # print("cid  ", self.c_id)
        # print("Energy")
        # print("NTT  ", NTT_Energy)
        # print("MM   ", MM_Energy)
        # print("MA   ", MA_Energy)
        # print("Auto ", Auto_Energy)
        # print("HBM  ", HBM_Energy)
        # print("DTU  ", DTU_Energy)
        # print("Total", total)
        return NTT_Energy, MM_Energy, MA_Energy, Auto_Energy, total

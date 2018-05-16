import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import metrics
import dataset


class Result:

    def __init__(self, config):
        self.path = config.get_result_path()
        self.dataset = dataset.Dataset(config.get_dataset_filename())
        self.dataset.load()
        self.df = self.load_results()
        self.data = self.load_data()
        self.df_coeffs = self.load_coeffs()
        self.testdata = self.data[self.df.row, :]


    def load_results(self):
        return pd.read_csv(self.path + "/results.csv")

    def load_data(self):
        file_path = self.dataset.get_feature_filename()
        shape = (self.dataset.size, self.dataset.count_features())
        return np.memmap(file_path, dtype=np.dtype('u1'), shape=shape)

    def load_coeffs(self):
        df_coeffs = pd.read_csv(self.path + "/coeffs.csv").as_matrix()
        return np.exp(df_coeffs)

    def get_coeffs(self, feature_range):
        return self.df_coeffs[1 + np.array(feature_range)]

    def gini(self):
        return round(metrics.gini_emblem_fast(
                                  self.df.target /self.df.exposure,
                                  self.df.prediction / self.df.exposure,
                                  self.df.exposure), 6) * 100

    def rmse(self):
        return round(metrics.root_mean_square_error(
                                  self.df.target,
                                  self.df.prediction,
                                  self.df.exposure), 6)

    def get_gini_curve(self, n=21):
        ginipath_filename = os.path.join(self.path, 'ginipath.csv')
        df = pd.read_csv(ginipath_filename)
        df.Gini *= 100
        return df.head(n)

    def plot_gini_curve(self, path, n=21):
        print('Plot Gini Curve')

        ginipath_filename = os.path.join(self.path, 'ginipath.csv')
        df = pd.read_csv(ginipath_filename)
        ar = np.arange(n)
        gini = df.head(n).Gini * 100
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.set_title('Gini Curve')
        ax.set_ylim([0, max(gini) * 1.1])
        ax.plot(range(0, n), gini, marker='o')
        ax.legend()
        ax.set_xticks(ar)

        filename = os.path.join('img', 'gini_path.png')
        plt.savefig(os.path.join(path, filename))
        plt.close()

        return filename

    def fill_missing_modalities(self, df, modalities):
        for i in range(len(modalities)):
            if i not in df.index:
                df.loc[i] = [0, 1, 1]
        return df

    def calculate_relativities(self, feature):
        df = self.df
        idx = self.dataset.get_feature_index(feature)
        modalities = self.dataset.get_modalities(feature)

        try:
            modalities = [float(m) for m in modalities]
            if sum([m - int(m) for m in modalities]) == 0:
                modalities = [int(m) for m in modalities]
        except Exception:
            # modalities are not integers -> that is perfectly ok
            pass

        df['f'] = self.testdata[:, idx]

        relativity = df.groupby(['f']).agg({
                                           'exposure': 'sum',
                                           'target': 'mean',
                                           'prediction': 'mean'
                                           })
        relativity = relativity.rename({
            'exposure': 'Exposure',
            'target': 'Target',
            'prediction': 'Prediction',
        }, axis=1)
        relativity.Exposure = relativity.Exposure.astype('int')
        relativity.Prediction /= df.target.mean()
        relativity.Prediction = relativity.Prediction.round(decimals=3)
        relativity.Target /= df.target.mean()
        relativity.Target = relativity.Target.round(decimals=3)
        relativity = self.fill_missing_modalities(relativity, modalities)
        relativity['Modalities'] = modalities
        relativity['Coefficients'] = self.get_coeffs(
            self.dataset.get_feature_range(feature)
        )
        relativity['Coefficients'] = relativity['Coefficients'] \
            .round(decimals=3)
        relativity = relativity.sort_values('Modalities')
        relativity = relativity.reset_index()
        relativity = relativity[['Modalities',
                                 'Coefficients',
                                 'Exposure',
                                 'Prediction',
                                 'Target']]
        return relativity

    def plot_relativities(self, feature, path):
        print("Plot Relativities ", feature)
        relativity = self.calculate_relativities(feature)
        ar = np.arange(relativity.Prediction.size)

        # Create chart
        fig, ax1 = plt.subplots(figsize=(10, 8))

        # Exposure on first axis
        ax1.bar(ar, relativity.Exposure, color='#fffca0', edgecolor='grey')
        ax1.set_ylim(ymax=relativity.Exposure.max() * 3)
        ax1.set_xticks(ar)
        ax1.set_xticklabels(labels=relativity.Modalities)
        ax1.set_ylabel('Weight')

        # Relativities on second axis
        ax2 = ax1.twinx()
        ax2.set_title(feature)
        ax2.plot(ar, relativity.Prediction, color="#0f600e", marker=".")
        ax2.plot(ar, relativity.Target, color="#c242f4", marker=".")
        ax2.plot(ar, relativity.Coefficients, color="#93ff9e", marker="^")
        ax2.axhline(y=1, color='black', linewidth=1, linestyle="dotted")
        ax2.set_ylim(ymin=0)
        ax2.set_ylabel('Values')

        filename = os.path.join(path, 'img', 'relativity_' + feature + '.png')
        plt.savefig(filename)
        plt.close()

        return os.path.join('img', 'relativity_' + feature + '.png')

    def plot_lift_curve(self, path, n_band=10):
        print("Plot Lift Curve")
        y = self.df.target
        y_pred = self.df.prediction
        weight = self.df.exposure

        if weight is None:
            weight = np.ones(y.shape[0])

        d = {'pred': list(y_pred), 'obs': list(y), 'weights': list(weight)}
        d = pd.DataFrame(d)
        d = d.dropna(subset=['obs', 'pred'])
        d = d.sort_values('pred', ascending=True)
        d.index = list(range(0, len(y_pred)))
        exp_cum = [0]
        for k in range(0, len(y_pred)):
            exp_cum.append(exp_cum[-1] + d.ix[k, 'weights'])
        s = exp_cum[-1]
        j = s // n_band
        m_pred, m_obs, m_weight = [], [], []
        k, k2 = 0, 0

        for i in range(0, n_band):
            k = k2
            for p in range(k, len(y_pred)):
                if exp_cum[p] < ((i + 1) * j):
                    k2 += 1
            temp = d.ix[range(k, k2), ]
            m_pred.append(sum(temp['pred'] * temp['weights']) /
                          sum(temp['weights']))
            m_obs.append(sum(temp['obs'] * temp['weights']) /
                         sum(temp['weights']))
            m_weight.append(temp['weights'].sum())

        fig, ax1 = plt.subplots(figsize=(10, 8))
        ax2 = ax1.twinx()
        ax1.set_title('Lift Curve')
        ax1.set_ylim([0, max(m_weight) * 3])
        # the histogram of the weigths
        ax1.bar(range(0, n_band), m_weight, color='#fffca0',
                edgecolor='grey')
        ax2.plot(range(0, n_band), m_pred, linestyle='--',
                 marker='o', color='b')
        ax2.plot(range(0, n_band), m_obs, linestyle='--',
                 marker='o', color='r')
        ax2.legend(labels=['Predicted', 'Observed'], loc=2)
        ax1.set_xlabel('Band')
        ax2.set_ylabel('Y values')
        ax1.set_ylabel('Weight')

        filename = os.path.join(path, 'img', 'lift_curve.png')
        fig.savefig(filename, bbox_inches='tight')
        plt.close()
        return os.path.join('img', 'lift_curve.png')

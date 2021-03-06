#include "Coefficients.h"

#include <fstream>

// Provide an absraction for the coefficient of a linear model. The class also
// provide a method (predict) to apply the model on a dataset and several
// metrics related to the coefficients (Norm2, CGini, Spread100/0, Spread95/5).
//
// Params :
//      - config : regression configuration ;
//      - coeffs : the list of coefficients fitted by the linear model ;
//      - weights : the total weight of training observations by modality ;
//      - selected_features : active set of features.

Coefficients::Coefficients(Config* config,
    const std::vector<float>& coeffs,
    const std::vector<float>& weights,
    const std::set<int>& selected_features) :
    config(config),
    coeffs(coeffs),
    weights(weights),
    selected_features(selected_features)
{
}

std::unique_ptr<ModelResult> Coefficients::predict(Dataset* dataset,
        const std::vector<int> &samples)
{
    uint8_t* x = dataset->get_x();
    float* weight = dataset->get_weight();
    float* y = dataset->get_y();
    ModelResult* result = new ModelResult(samples.size(), config);
    int p = config->p;
    int obs = 0;
    for(int i : samples){
        float dp = coeffs[0];
        for(int j : selected_features){
            int k = config->offsets[j] + x[p * i + j];
            dp += coeffs[k];
        }
        result->setObservation(obs, i, y[i], exp(dp) * weight[i], weight[i],
                               dp);
        ++obs;
    }
    return std::unique_ptr<ModelResult>(result);
}

int Coefficients::getMinCoeff()
{
    int minidx = -1;
    float minvalue = 0;
    for(int i : selected_features){
        float s = getCoeffGini(i);
        if(minidx == -1 || s < minvalue){
            minvalue = s;
            minidx = i;
        }
    }
    return minidx;
}

float Coefficients::getCoeffNorm2(int feature)
{
    if(feature < 0){
        return 0;
    }

    float sc = 0;
    float sw = 0;
    for(int j = config->offsets[feature]; j < config->offsets[feature + 1];
        j++){
        float c = std::exp(coeffs[j]);
        float w = weights[j];
        sc += c * c * w;
        sw += w;
    }
    return std::sqrt(sc / sw);
}

float Coefficients::getCoeffGini(int feature)
{
    if(feature < 0){
        return 0;
    }

    int nb_coeffs = config->offsets[feature + 1] - config->offsets[feature];
    std::vector<int> feature_idx(nb_coeffs);
    for(int i = 0; i < nb_coeffs; i++){
        feature_idx[i] = config->offsets[feature] + i;
    }
    std::sort(feature_idx.begin(), feature_idx.end(),
        [this](size_t i, size_t j) {
            return this->coeffs[i] < this->coeffs[j];
        }
    );

    float g = 0;
    float sc = 0;
    float sw = 0;
    for(int i : feature_idx){
        float w = weights[i];
        float c = std::exp(coeffs[i]) * w;
        g += w * (2 * sc + c);
        sc += c;
        sw += w;
    }
    g = 1 - g / (sc * sw);
    g = g < 0.0000001 ? 0 : g;
    return g * 100;
}

float Coefficients::getSpread100(int feature)
{
    if(feature < 0){
        return 0;
    }

    float minvalue = 100000000;
    float maxvalue = 0;

    for(int j = config->offsets[feature]; j < config->offsets[feature + 1];
        j++){
        float c = std::exp(coeffs[j]);
        if(c < minvalue) minvalue = c;
        if(c > maxvalue) maxvalue = c;
    }
    return float(std::round((maxvalue / minvalue - 1) * 10000)) / 100;
}

float Coefficients::getSpread95(int feature)
{
    if(feature < 0){
        return 0;
    }

    int nb_coeffs = config->offsets[feature + 1] - config->offsets[feature];
    std::vector<int> feature_idx(nb_coeffs);
    for(int i = 0; i < nb_coeffs; i++){
        feature_idx[i] = config->offsets[feature] + i;
    }
    std::sort(feature_idx.begin(), feature_idx.end(),
        [this](size_t i, size_t j) {
            return this->coeffs[i] < this->coeffs[j];
        }
    );
    std::vector<float> cum_weight(nb_coeffs);
    for(int i = 0; i < nb_coeffs; i++){
        cum_weight[i] = (i > 0 ? cum_weight[i - 1] : 0) +
                        (weights[feature_idx[i]] / weights[0]);
    }
    float minvalue = 0;
    float maxvalue = 0;
    for(int i = 0; i < nb_coeffs; i++){
        if(cum_weight[i] > 0.05){
            minvalue = std::exp(coeffs[feature_idx[i]]);
            break;
        }
    }
    for(int i = 0; i < nb_coeffs; i++){
        if(cum_weight[i] > 0.95){
            maxvalue = std::exp(coeffs[feature_idx[i]]);
            break;
        }
    }
    return float(std::round((maxvalue / minvalue - 1) * 10000)) / 100;
}

void Coefficients::saveResults()
{
    std::ofstream coeffFile;
    coeffFile.open(config->resultPath + "coeffs.csv", std::ios::out);
    coeffFile << "Coeffs" << std::endl;
    for(float c : coeffs){
        coeffFile << c << std::endl;
    }
    coeffFile.close();
}

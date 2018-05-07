#ifndef DATASET_H_
#define DATASET_H_

#include <string>
#include <random>
#include <vector>

#include "array.h"
#include "config.h"

class Dataset
{
public:
    float testPct;
    std::vector<int> train;
    std::vector<int> test;
    std::mt19937 generator;
    std::uniform_int_distribution<std::mt19937::result_type> random;
    Array<uint8_t>* x_data;
    Array<float>* exposure_data;
    Array<float>* y_data;

    Dataset();
    Dataset(Config* config, float testPct);
    int next();
    void filterNonZeroTarget();
};

#endif  // DATASET_H_
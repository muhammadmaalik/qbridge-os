package com.axesq.qbridge;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * QBridge Enterprise Java SDK
 * Wraps Qiskit Quantum Hardware simulators into native Java Objects using REST APIs.
 */
public class QBridgeClient {
    private final String apiEndpoint;
    private final HttpClient httpClient;

    public QBridgeClient(String apiEndpoint) {
        // Strip trailing slashes to prevent malformed URI routing
        this.apiEndpoint = apiEndpoint.endsWith("/") ? apiEndpoint.substring(0, apiEndpoint.length() - 1) : apiEndpoint;
        
        // Build an asynchronous HTTP engine
        this.httpClient = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_2)
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    }

    private String getRaw(String path) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .GET()
            .uri(URI.create(this.apiEndpoint + path))
            .header("Accept", "application/json")
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        
        if (response.statusCode() != 200) {
            throw new RuntimeException("QBridge Network Disconnect: Status " + response.statusCode());
        }
        return response.body();
    }

    private String postRaw(String path, String jsonPayload) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .POST(HttpRequest.BodyPublishers.ofString(jsonPayload))
            .uri(URI.create(this.apiEndpoint + path))
            .header("Content-Type", "application/json")
            .header("Accept", "application/json")
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        
        if (response.statusCode() != 200) {
            throw new RuntimeException("QBridge HTTP POST Reject: Status " + response.statusCode());
        }
        return response.body();
    }

    /**
     * Executes a remote Variational Quantum Eigensolver (VQE) algorithm.
     */
    public String simulateMolecule(String molecule, double bondDistance, double temp) {
        System.out.println("[QBridge Java] Compiling structural blueprint targeting: " + molecule);
        String payload = String.format("{\"molecule\": \"%s\", \"bond_distance\": %f, \"temperature\": %f}", molecule, bondDistance, temp);
        try {
            return postRaw("/api/services/chemistry", payload);
        } catch (Exception e) {
            return "{\"success\": false, \"error\": \"" + e.getMessage() + "\"}";
        }
    }

    /**
     * Executes a Quantum Pathfinder protocol mapping drone routing parameters.
     */
    public String runRobotics(int gridSize) {
        System.out.println("[QBridge Java] Injecting hardware grid [" + gridSize + "x" + gridSize + "]...");
        String payload = String.format("{\"grid_size\": %d, \"obstacles\": []}", gridSize);
        try {
            return postRaw("/api/services/robotics", payload);
        } catch (Exception e) {
            return "{\"success\": false, \"error\": \"" + e.getMessage() + "\"}";
        }
    }

    /**
     * Feeds arrays into a high-dimensional Quantum SVM.
     */
    public String runMachineLearning(String tensorJsonArray) {
        System.out.println("[QBridge Java] Sending classical tensor array to QPU...");
        String payload = String.format("{\"tensor_array\": %s}", tensorJsonArray);
        try {
            return postRaw("/api/services/ml", payload);
        } catch (Exception e) {
            return "{\"success\": false, \"error\": \"" + e.getMessage() + "\"}";
        }
    }

    // ==========================================
    // Example Developer Usage:
    // ==========================================
    public static void main(String[] args) {
        // Java developers link securely without writing socket logic
        QBridgeClient client = new QBridgeClient("https://axesq.us");

        String result = client.simulateMolecule("H2O", 0.96, 298.0);
        System.out.println("\n--- Java Chemistry Pipeline ---");
        System.out.println(result);
        
        System.out.println("\n--- Java Drone Routing Pipeline ---");
        System.out.println(client.runRobotics(4));
    }
}
